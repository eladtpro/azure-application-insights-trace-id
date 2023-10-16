import azure.functions as func
import logging
import json
import http.client
from datetime import datetime
from urllib.parse import urlparse
# from opentelemetry import trace
# import os
# from azure.monitor.opentelemetry import configure_azure_monitor
# configure_azure_monitor(
#     connection_string=os.environ['OPEN_TELEMETRY_CONNECTION_STRING'],
# )

# # Get a tracer for the current module.
# tracer = trace.get_tracer(__name__)
# with tracer.start_as_current_span("test"):
#     print("Hello world from OpenTelemetry Python!")


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="start")
@app.route(route="start")
def start(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info(f'[start] Python HTTP trigger function processed a request. next url')
    log_request(req, context)
    connection, headers = get_connection(req.url, dict(req.headers))
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
    return connection.getresponse()


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
    if url_parts.scheme == 'http':
        connection = http.client.HTTPConnection(url_parts.netloc)
    elif url_parts.scheme == 'https':
        connection = http.client.HTTPSConnection(url_parts.netloc)
        # connection = http.client.HTTPSConnection('func-azure-monitor.azurewebsites.net')
    else:
        error = f'Error: {url_parts.scheme} is not supported'
        logging.error(error)
        return func.HttpResponse(error, status_code=400)

    # remove auth headers
    if 'authorization' in headers:
        del headers['authorization']
    headers['Content-type'] = 'application/json'
    
    # HACK: create generator function thats creates trace-id
    # traceparent = f'00-{datetime.now().strftime("%Y%m%d%H%M%S%f")}-b4b37b64bb3f6141-00'
    if 'traceparent' not in headers:
        headers['traceparent'] = '00-480e22a2781fe54d992d878662248d94-b4b37b64bb3f6141-00'

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
