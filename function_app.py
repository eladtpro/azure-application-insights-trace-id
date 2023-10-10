import azure.functions as func
import logging
import json
import http.client


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="start")
@app.route(route="start")
def start(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('[start] Python HTTP trigger function processed a request.')
    # url = 'https://func-azure-monitor.azurewebsites.net/api/headers'
    headers = dict(req.headers)
    headers['Content-type'] = 'application/json'
    if 'trace-id' not in headers:
        headers['trace-id'] = req.params.get('correlation-id') or headers.get('x-operation-id') or '12345678-9ABC-1234-5678-9ABCDEFGHIJK'

    connection = http.client.HTTPSConnection('func-azure-monitor.azurewebsites.net')
    connection.request('GET', '/api/headers', headers=headers)    

    response = connection.getresponse()
    if response.status == 200:
        res = response.read().decode()
        logging.info(res)        
        return func.HttpResponse(
                res,
                mimetype="application/json",
                status_code=200)
    else:
        logging.error(headers)
        return func.HttpResponse(
          f'[start] Error: {response.status} - {response.reason}',
          status_code=response.status)


# @app.function_name(name="headers")
# @app.route(route="headers")
# @app.service_bus_topic_output(arg_name="message", connection="ServiceBusConnection", queue_name="new")
# def headers(req: func.HttpRequest, message: func.Out[str]) -> func.HttpResponse:
#     logging.info('[headers] Python HTTP trigger function processed a request.')

#     headersAsDict = dict(req.headers)
#     wrapper = {
#         "source": 'headers',
#         "headers": headersAsDict
#     }

#     headersAsStr = json.dumps(wrapper, indent=2)
#     logging.info(headersAsStr)
#     message.set(headersAsStr)

#     return func.HttpResponse(
#             headersAsStr,
#             mimetype="application/json",
#             status_code=200
#     )

# @app.function_name(name="dequeue")
# @app.route(route="dequeue")
# @app.service_bus_queue_trigger(arg_name="msg", queue_name="new", connection="ServiceBusConnection")
# def dequeue(msg: func.ServiceBusMessage) -> None:
#     logging.info('[dequeue] Python ServiceBus queue trigger function processed a request.')
#     logging.info('Python ServiceBus queue trigger processed message: %s',
#                  msg.get_body().decode('utf-8'))
