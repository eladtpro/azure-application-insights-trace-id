import azure.functions as func
import logging
import json
import http.client
import os
from datetime import datetime
from urllib.parse import urlparse
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics, propagators, context


configure_azure_monitor(
    connection_string=os.environ['OPEN_TELEMETRY_CONNECTION_STRING'],
)

# Get a tracer for the current module.
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("test"):
    print("Hello world from OpenTelemetry Python!")

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="start")
@app.route(route="start")
def start(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info(f'[start] Python HTTP trigger function processed a request. next url')
    log_request(req, context)
    url_parts = urlparse(req.url)
    if url_parts.scheme == 'http':
        connection = http.client.HTTPConnection(url_parts.netloc)
    elif url_parts.scheme == 'https':
        connection = http.client.HTTPSConnection(url_parts.netloc) # connection = http.client.HTTPSConnection('func-azure-monitor.azurewebsites.net')
    else:
        error = f'Error: {url_parts.scheme} is not supported'
        logging.error(error)
        return func.HttpResponse(error, status_code=400)

    headers = dict(req.headers)
    # remove auth headers
    if 'authorization' in headers:
        del headers['authorization']
    headers['Content-type'] = 'application/json'
    
    if 'trace-id' not in headers:
        time_string = datetime.now().strftime('HH%HMM%MSS%S')

        headers['parent-id'] = headers['trace-id'] = f'12345678-9ABC-1234-5678-{time_string}'
        # headers['trace-id'] = req.params.get('correlation-id') or headers.get('x-operation-id') or '12345678-9ABC-1234-5678-9ABCDEFGHIJK'
        # headers['x-operation-id'] = headers['trace-id']

    logging.info(f'START: {headers["trace-id"]}')

    connection.request('GET', '/api/enqueue', headers=headers)    
    response = connection.getresponse()

    if response.status >= 200 and response.status < 300 :
        res = response.read().decode()
        logging.info(res)        
    else:
        res =  json.dumps({error: f'[start] {response.status} - {response.reason}'}, indent=2)
        logging.error(res)
    
    return func.HttpResponse(
            res,
            mimetype="application/json",
            status_code=response.status)
    

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
    trace_id = 'UNKNOWN'
    if 'trace-id' in obj['headers']:
        trace_id = obj['headers']['trace-id']
    logging.info(f'END: {trace_id}')


def log_request(req: func.HttpRequest, context: func.Context) -> str:
    dict_headers = dict(req.headers)
    trace_data = {
        'ctx_func_dir': context.function_directory,
        'ctx_invocation_id': context.invocation_id,
        'ctx_trace_context_Traceparent': context.trace_context.Traceparent,
        'ctx_trace_context_Tracestate': context.trace_context.Tracestate,
        'ctx_retry_context_RetryCount': context.retry_context.retry_count,
        'ctx_retry_context_MaxRetryCount': context.retry_context.max_retry_count,
    }

    wrapper = {
        'ctx_func_name': context.function_name or 'NO_FUNC_NAME',
        'method': req.method or 'NO_METHOD',
        "route_params": req.route_params or {},
        "params": req.params or {},
        "headers": dict_headers or {},
        "trace": trace_data or {},
    }

    log_entry = json.dumps(wrapper, indent=2)
    logging.info(log_entry)
    return log_entry
