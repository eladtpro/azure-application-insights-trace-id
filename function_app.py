import azure.functions as func
import logging
import json
import http.client
from datetime import datetime
from urllib.parse import urlparse
# import os
# from azure.monitor.opentelemetry import configure_azure_monitor
# from opentelemetry import trace
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import (BatchSpanProcessor, ConsoleSpanExporter)
# from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


# configure_azure_monitor(
#     connection_string=os.environ['OPEN_TELEMETRY_CONNECTION_STRING'],
# )

# trace.set_tracer_provider(TracerProvider())
# trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

# tracer = trace.get_tracer(__name__)
# prop = TraceContextTextMapPropagator()
# carrier = {}

# # Injecting the context into carrier and send it over
# with tracer.start_as_current_span("first-span") as span:
#     prop.inject(carrier=carrier)
#     print("Carrier after injecting span context", carrier)

# # Extracting the remote context from carrier and starting a new span under same trace.
# ctx = prop.extract(carrier=carrier)
# with tracer.start_as_current_span("next-span", context=ctx):
#     pass


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="start")
@app.route(route="start")
def start(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info(f'[start] Python HTTP trigger function processed a request. next url')
    log_request(req, context)
    connection, headers = get_connection(req.url, dict(req.headers))

    if 'traceparent' not in headers:
        json_response = json.dumps({'error': 'traceparent header not found'})
        logging.error(json_response)
        return func.HttpResponse(
                json_response,
                mimetype="application/json",
                status_code=406)

    if 'x-appgw-trace-id' in headers:
        tx = headers['x-appgw-trace-id']
        traceparent = headers['traceparent']

        parts = traceparent.split('-')
        if len(parts) != 4:
            json_response = json.dumps({'error': 'traceparent header is invalid'})
            logging.error(json_response)
            return func.HttpResponse(
                    json_response,
                    mimetype="application/json",
                    status_code=406
            )
        if parts[1] != tx:
            parts[1] = tx # => 00-{tx}-{trace_state}-01
            headers['traceparent-original'] = traceparent
            headers['traceparent'] = '-'.join(parts)
            logging.info(f'UPDATE: {headers["traceparent-original"]} => {headers["traceparent"]}')

    
    logging.info(f'START: {headers["traceparent"]}')
    connection.request('GET', '/api/enqueue', headers=headers)    
    res =  connection.getresponse()

    return func.HttpResponse(
            res.read().decode('utf-8'),
            mimetype="application/json",
            status_code=200
    )
    

@app.function_name(name="enqueue")
@app.route(route="enqueue")
@app.service_bus_queue_output(arg_name="message", connection="ServiceBusConnection", queue_name="new")
def enqueue(req: func.HttpRequest, context: func.Context, message: func.Out[str]) -> func.HttpResponse:
    logging.info('[enqueue] Python HTTP trigger function processed a request.')
    log_entry = log_request(req, context)
    message.set(log_entry)

    return func.HttpResponse(
            log_entry,
            mimetype="application/json",
            status_code=200
    )


@app.function_name(name="dequeue")
@app.service_bus_queue_trigger(arg_name="msg", connection="ServiceBusConnection", queue_name="new")
def dequeue(msg: func.ServiceBusMessage) -> None:
    logging.info('[dequeue] Python ServiceBus queue trigger function processed a request.')
    logging.info('Python ServiceBus queue trigger processed message: %s', msg.get_body().decode('utf-8'))

    obj = json.loads(msg.get_body().decode('utf-8'))
    connection, headers = get_connection(obj['url'], obj['headers'])

    connection.request('POST', '/api/end', headers=headers, body=msg.get_body().decode('utf-8'))    
    response = connection.getresponse()
    logging.info(f'DEQUEUE: {headers["traceparent"], response.status, response.reason}')
    logging.info(f'DEQUEUE: {response.read().decode("utf-8")}')


@app.function_name(name="end")
@app.route(route="end")
def end(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info('[end] Python HTTP trigger function processed a request.')
    log_request(req, context)
    logging.info(f'END: {req.headers["traceparent"]}')

    return func.HttpResponse(
            "END",
            mimetype="application/json",
            status_code=200
    )


def get_connection(url: str, headers: dict) -> http.client.HTTPConnection or http.client.HTTPSConnection:
    url_parts = urlparse(url)
    if url_parts.scheme == 'http': # validate scheme
        connection = http.client.HTTPConnection(url_parts.netloc)
    elif url_parts.scheme == 'https':
        connection = http.client.HTTPSConnection(url_parts.netloc)
    else:
        error = f'Error: {url_parts.scheme} is not supported'
        logging.error(error)
        return func.HttpResponse(error, status_code=400)

    if 'authorization' in headers: # remove auth headers
        del headers['authorization']
    headers['Content-type'] = 'application/json'
    return connection, headers
    

def log_request(req: func.HttpRequest, context: func.Context) -> str:
    dict_headers = dict(req.headers)
    trace_data = {
        'ctx_func_dir': context.function_directory,
        'ctx_invocation_id': context.invocation_id,
        'ctx_trace_context_trace_parent': context.trace_context.trace_parent,
        'ctx_trace_context_trace_state': context.trace_context.trace_state,
        'ctx_retry_context_RetryCount': context.retry_context.retry_count,
        'ctx_retry_context_MaxRetryCount': context.retry_context.max_retry_count,
    }

    wrapper = {
        'url': req.url,
        'ctx_func_name': context.function_name or 'NO_FUNC_NAME',
        'method': req.method or 'NO_METHOD',
        "route_params": req.route_params or {},
        "params": req.params or {},
        "headers": dict_headers or {},
        "trace": trace_data or {},
    }

    log_entry = json.dumps(wrapper) #, indent=2)
    logging.info(log_entry)
    return log_entry
