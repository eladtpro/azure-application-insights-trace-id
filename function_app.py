import azure.functions as func
import logging
import json
import http.client
# import requests


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="headers")
@app.route(route="headers")
def headers(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('[headers] Python HTTP trigger function processed a request.')

    headersAsDict = dict(req.headers)
    headersAsStr = json.dumps(headersAsDict, indent=2)
    logging.info(headersAsStr)

    return func.HttpResponse(
            headersAsStr,
            mimetype="application/json",
            status_code=200
    )

@app.function_name(name="caller")
@app.route(route="caller")
def caller(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('[caller] Python HTTP trigger function processed a request.')
    # url = 'https://func-azure-monitor.azurewebsites.net/api/headers'
    headers = dict(req.headers)
    headers['Content-type'] = 'application/json'
    headers['trace-id'] = req.params.get('correlation-id') or '12345678-9ABC-1234-5678-9ABCDEFGHIJK'

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
          f'[caller] Error: {response.status} - {response.reason}',
          status_code=response.status)