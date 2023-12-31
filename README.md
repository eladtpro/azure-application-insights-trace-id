![Azure Application Insights](assets/application-map.png)
# Distributed tracing in-action (a.k.a trace-context propagation)


## In this article
[Distributed tracing in a nutshell](#what)  
[Scenario - trace in action](#scenario)  
[W3C: Trace Context specification](#spec)  
[Azure Web Application Firewall on Azure Application Gateway - Overriding transaction-id (Optional)](#waf)
[Further Reading](#further)  


## <a name="what"></a>Distributed tracing in a nutshell  
![Distributed Tracing](assets/tracing_trace_spans.png)

Microservices architecture comes with challenges, including the complexity of troubleshooting failures of each microservice over a distributed system composed of a chain of microservices.  

*Distributed tracing* helps isolate a specific user transaction and track its journey through the application stack.  


***Trace***: A ***trace*** is a tree of ***spans***. It is a collective of observable signals showing the path of work through a system.  
A ***trace*** is distinguishable by a unique 16-byte sequence called a `trace-id`.  

***Span***: A span represents a single operation in a ***trace***. A span could describe an HTTP request, a remote procedure call (RPC), a database query, etc.  
A ***span*** is distinguishable by a unique 8-byte sequence called a `span-id` or `parent-id`.  

***traceparent*** header, The *traceparent* header uses the Augmented Backus-Naur Form (ABNF) notation of [RFC5234](https://www.w3.org/TR/trace-context/#bib-rfc5234) and is composed of four sub-fields:  

```
# version - trace-id - span-id - traceflags  

00-480e22a2781fe54d992d878662248d94-b4b37b64bb3f6141-00
```

* ***version*** (8-bit): trace context version that the system has adopted. The current is 00.

* ***trace-id*** (16-byte array): the ID of the whole trace. It's used to identify a distributed trace globally through a system.

* ***parent-id*** or ***span-id*** (8-byte array): used to identify the parent of the current span on incoming requests or the current span on an outgoing request.

* ***trace-flags*** (8-bit): flags that represent recommendations of the caller. They can also be considered the caller's recommendations and are strict for three reasons: trust and abuse, bugs in the caller, or different load between caller and callee service.

> NOTE: all the fields are encoded as hexadecimal

<!-- ![Trace](assets/trace-example.png) -->


---


## <a name="scenario"></a>Scenario - trace in action  

Application Performance Monitoring (APM) with Azure Monitor Application Insights end-to-end transaction.

### Azure Resources:  
![Function App](assets/function-app.png)
![Service Bus](assets/ServiceBus.png)
![Application Insights](assets/app-insights.png)
![Log Analytics Workspace](assets/log-analytics.png)

Functions, Service Bus queue, Applciation Insights, and Log Analytics Workspace

***Azure Function Service***: Azure Functions is an event-driven, serverless compute platform that helps you develop more efficiently using the programming language of your choice. Focus on core business logic with the highest level of hardware abstraction.  

***Azure Service Bus queue service***: Queues offer First In, First Out (FIFO) message delivery to one or more competing consumers. That is, receivers typically receive and process messages in the order in which they were added to the queue. And, only one message consumer receives and processes each message.  

***Azure Monitor Application Insights***: Azure Monitor Application Insights, Application Performance Monitoring (APM) subsystem, a feature of Azure Monitor, excels in Application Performance Management (APM) for live web applications.  

***Azure Log Analytics Workspace***: A Log Analytics workspace is a unique environment for log data from Azure Monitor and other Azure services, such as Microsoft Sentinel and Application Insights. Each workspace has its own data repository and configuration but might combine data from multiple services.  


### The Flow

![Flow](assets/flow.png)

The code file defines an Azure Function App that consists of four functions that handle both Service Bus queues and HTTP requests:  

***start***: This function is triggered by an HTTP request with the route /start. It logs the request and then makes a GET request to another endpoint with the same headers. 
start phase also injects the Azure Application Gateway transaction header into the ***traceparent*** header:  
`version-trace-id-span-id-traceflags`
into
`version-x_appgw_trace_id-span-id-traceflags`

***enqueue***: This function is triggered by an HTTP request with the route /enqueue. It logs the request and then sends a message to an Azure Service Bus queue.  

***dequeue***: This function is triggered by a message in an Azure Service Bus queue. It logs the message and then makes a POST request to another endpoint with the same headers.  

***end***: This function is triggered by an HTTP request with the route /end. It logs the request and returns a HTTP response with the body "END".  


#### End-to-end transaction view
![End to End Transaction](assets/end2end-tx.png)



---


### Test

##### Trace Headers
***traceparent***: `00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01`
***tracestate***: `rojo=00f067aa0ba902b7,congo=t61rcWkgMzE`

`https://<your-func>.azurewebsites.net`


---

![W3C](assets/W3C-World-Wide-Web.png)
## <a name="spec"></a>W3C: Trace Context specification


> ***Distributed tracing*** is a methodology implemented by tracing tools to follow, analyze and debug a transaction across multiple software components. Typically, a [*distributed trace*](#distrace) traverses more than one component which requires it to be uniquely identifiable across all participating systems. Trace context propagation passes along this unique identification.


> <a name="distrace"></a> ***Distributed trace***, A distributed trace is a set of events, triggered as a result of a single logical operation, consolidated across various components of an application. A distributed trace contains events that cross process, network and security boundaries. A distributed trace may be initiated when someone presses a button to start an action on a website - in this example, the trace will represent calls made between the downstream services that handled the chain of requests initiated by this button being pressed.

### Abstract
This specification defines standard HTTP headers and a value format to propagate context information that enables **distributed tracing scenarios**. The specification standardizes how context information is sent and modified between services. Context information uniquely identifies individual requests in a distributed system and also defines a means to add and propagate provider-specific context information.

### Problem Statement

The problem of distributed tracing in modern, highly distributed applications and the need for a standardized solution. In the past, most applications were monitored by a single tracing vendor and stayed within a single platform provider's boundaries.  
However, as applications become more distributed and leverage multiple middleware services and cloud platforms, the lack of a common standard for trace context propagation has created interoperability issues.  

### Solution Space
The proposed solution is the [trace context specification](https://www.w3.org/TR/trace-context/), which defines a universally agreed-upon format for exchanging trace context propagation data.  
This trace context solves several problems by providing a unique identifier for traces and requests, enabling the linking of trace data from multiple providers. It also offers a mechanism to forward vendor-specific trace data and establishes an industry standard that intermediaries, platforms, and hardware providers can support. This standardized approach enhances visibility into the behavior of distributed applications, aiding in problem diagnosis and performance analysis. Interoperability is essential for managing modern microservices-based applications.  

Tracing tools can behave in two ways: They must at least propagate the ***traceparent*** and ***tracestate*** headers to ensure trace continuity (forwarding a trace). They can also choose to participate in a trace by modifying these headers with proprietary information (participating in a trace). The behavior of tracing tools can vary for each individual request they monitor.


### The trace context standard
The [W3C Trace Context](https://www.w3.org/TR/trace-context/) specification defines a standard to HTTP headers and formats to propagate the distributed tracing context information. It defines two fields that should be propagated in the http request's header throughout the trace flow. Take a look below at the standard definition of each field:

The trace context is split into two parts: "traceparent," which describes the position of incoming requests in the trace graph, and "tracestate," which extends traceparent with vendor-specific data in the form of name/value pairs.



* ***traceparent***: ***traceparent*** describes the position of the incoming request in its trace graph in a portable, fixed-length format. Its design focuses on fast parsing. Every tracing tool MUST properly set ***traceparent*** even when it only relies on vendor-specific information in tracestate


* ***tracestate***: extends traceparent with vendor-specific data represented by a set of name/value pairs. Storing information in tracestate is optional.


---

## <a name="waf"></a>Azure Web Application Firewall on Azure Application Gateway - Overriding transaction-id (Optional)

![Azure Web Application Firewall on Azure Application Gateway - override headers](assets/header-rewrite-overview.png)
In some cases we want to override the [*traceparent header*](https://www.w3.org/TR/trace-context/#traceparent-header) so its value will fit our internal transaction-id, in this section we will use Azure Web Application Firewall (WAF) which is a gateway for all incoming requests,  to overide the transaction-id.   
Application Gateway allows you to rewrite selected content of requests and responses. With this feature, you can translate URLs, query string parameters as well as modify request and response headers. It also allows you to add conditions to ensure that the URL or the specified headers are rewritten only when certain conditions are met. These conditions are based on the request and response information.


for this case we will use Azure Application Gateway rewrite set,
In this rule we will create new traceparent header with the Azure AGW builtin transaction request header "xappgw-trace-id":

![Header rewrite rule set](assets/update-rewrite-set.png)


---

## <a name="further">Further Reading

### Azure Monitor  

[Application Insights overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
<sub>Azure Monitor Application Insights, a feature of [Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/overview), excels in Application Performance Management (APM) for live web applications.</sub>

[Log Analytics workspace overview](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-workspace-overview)  
<sub>A Log Analytics workspace is a unique environment for log data from Azure Monitor and other Azure services, such as Microsoft Sentinel and Microsoft Defender for Cloud. Each workspace has its own data repository and configuration but might combine data from multiple services.</sub>

### Azure Microservices

[Microservices on Azure](https://azure.microsoft.com/en-us/solutions/microservice-applications/)

[Azure Service Bus output binding for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-service-bus-output?tabs=python-v2%2Cisolated-process%2Cnodejs-v4%2Cextensionv5&pivots=programming-language-python)  
<sub>Use Azure Service Bus output binding to send queue or topic messages.</sub>

[Tutorial: Use identity-based connections instead of secrets with triggers and bindings](https://learn.microsoft.com/en-us/azure/azure-functions/functions-identity-based-connections-tutorial-2)

[host.json settings](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-service-bus?tabs=isolated-process%2Cfunctionsv2%2Cextensionv3&pivots=programming-language-python#hostjson-settings)  
<sub>This section describes the configuration settings available for this binding, which depends on the runtime and extension version.</sub>  

[Azure Service Bus output binding for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-service-bus-output?tabs=python-v2%2Cisolated-process%2Cnodejs-v4%2Cextensionv5&pivots=programming-language-python)  


[Azure Functions Python developer guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level&pivots=python-mode-decorators)  
<sub>This guide is an introduction to developing Azure Functions by using Python.</sub>


### Azure Application Gateway

[Configure App Service with Application Gateway](https://learn.microsoft.com/en-us/azure/application-gateway/configure-web-app?tabs=defaultdomain%2Cazure-portal)
<sub>Application gateway allows you to have an App Service app or other multi-tenant service as a backend pool member. In this article, you learn to configure an App Service app with Application Gateway</sub>

[What is Azure Web Application Firewall on Azure Application Gateway?](https://learn.microsoft.com/en-us/azure/web-application-firewall/ag/ag-overview)
<sub>Azure Web Application Firewall (WAF) on Azure Application Gateway provides centralized protection of your web applications from common exploits and vulnerabilities. Web applications are increasingly targeted by malicious attacks that exploit commonly known vulnerabilities. SQL injection and cross-site scripting are among the most common attacks.</sub>

[Rewrite HTTP request and response headers with Azure Application Gateway - Azure portal](https://learn.microsoft.com/en-us/azure/application-gateway/rewrite-http-headers-portal)
<sub>This article describes how to use the Azure portal to configure an [Application Gateway v2 SKU](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-autoscaling-zone-redundant) instance to rewrite the HTTP headers in requests and responses.</sub>

[Rewrite HTTP headers and URL with Application Gateway](https://learn.microsoft.com/en-us/azure/application-gateway/rewrite-http-headers-url)
<sub>Application Gateway allows you to rewrite selected content of requests and responses. With this feature, you can translate URLs, query string parameters as well as modify request and response headers. It also allows you to add conditions to ensure that the URL or the specified headers are rewritten only when certain conditions are met. These conditions are based on the request and response information.</sub>

[Custom rules for Azure Web Application Firewall on Azure Front Door](https://learn.microsoft.com/en-us/azure/web-application-firewall/afds/waf-front-door-custom-rules)
<sub>Azure Web Application Firewall on Azure Front Door allows you to control access to your web applications based on the conditions you define. A custom web application firewall (WAF) rule consists of a priority number, rule type, match conditions, and an action.</sub>


### Tracing Standarts  

[W3C Trace Context](https://www.w3.org/TR/trace-context/#trace-id)  

[OpenTelemetry Concepts](https://opentelemetry.io/docs/concepts/)  
<sub>Data sources and key components of the OpenTelemetry project</sub>

[Grafana: A beginner's guide to distributed tracing and how it can increase an application's performance](https://grafana.com/blog/2021/01/25/a-beginners-guide-to-distributed-tracing-and-how-it-can-increase-an-applications-performance/)  
<sub>Outline of the basics around distributed tracing. Along with explaining how tracing works, we also address why developers should work to incorporate distributed tracing into their applications and how investing the money and time to build the infrastructure and install the code for tracing can increase an application’s performance.</sub>  

[What is distributed tracing and telemetry correlation?](https://learn.microsoft.com/en-us/azure/azure-monitor/app/distributed-tracing-telemetry-correlation)  
<sub>Modern cloud and [microservices](https://azure.com/microservices) architectures have enabled simple, independently deployable services that reduce costs while increasing availability and throughput. However, it has made overall systems more difficult to reason about and debug. Distributed tracing solves this problem by providing a performance profiler that works like call stacks for cloud and microservices architectures.</sub>


### Python and 3rd Party
[OpenCensus - Tracing](https://opencensus.io/tracing/)  
<sub>Tracing tracks the progression of a single user request as it is handled by other services that make up an application.</sub>  

[Monitor a distributed system by using Application Insights and OpenCensus](https://learn.microsoft.com/en-us/azure/architecture/guide/devops/monitor-with-opencensus-application-insights)  
<sub>This article describes a distributed system that's created with Azure Functions, Azure Event Hubs, and Azure Service Bus. It provides details about how to monitor the end-to-end system by using [OpenCensus for Python](https://github.com/census-instrumentation/opencensus-python) and Application Insights. This article also introduces distributed tracing and explains how it works by using Python code examples. The fictional company, Contoso, is used in the architecture to help describe the scenario.</sub>  

[Monitor a distributed system by using Application Insights and OpenCensus](https://learn.microsoft.com/en-us/azure/architecture/guide/devops/monitor-with-opencensus-application-insights)
<sub>This article describes a distributed system that's created with Azure Functions, Azure Event Hubs, and Azure Service Bus. It provides details about how to monitor the end-to-end system by using [OpenCensus for Python](https://github.com/census-instrumentation/opencensus-python) and Application Insights. This article also introduces distributed tracing and explains how it works by using Python code examples. The fictional company, Contoso, is used in the architecture to help describe the scenario.</sub>

[OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)

[Lelis Dev - trace context](https://luizlelis.com/blog/tracecontext)  
<sub>Using W3C Trace Context standard in distributed tracing</sub>

[WaveFront Distributed Tracing Key Concepts](https://docs.wavefront.com/trace_data_details.html)  
<sub>Get to know the concepts around distributed tracing.</sub>

[Azure Functions Python developer guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level&pivots=python-mode-decorators)  
<sub>This guide is an introduction to developing Azure Functions by using Python. The article assumes that you've already read the [Azure Functions developers guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference).</sub>

[Set up Azure Monitor for your Python application](https://learn.microsoft.com/en-us/previous-versions/azure/azure-monitor/app/opencensus-python)  
<sub>Azure Monitor supports distributed tracing, metric collection, and logging of Python applications.  
Microsoft's supported solution for tracking and exporting data for your Python applications is through the [OpenCensus Python SDK](https://learn.microsoft.com/en-us/previous-versions/azure/azure-monitor/app/opencensus-python#introducing-opencensus-python-sdk) via the [Azure Monitor exporters](https://learn.microsoft.com/en-us/previous-versions/azure/azure-monitor/app/opencensus-python#instrument-with-opencensus-python-sdk-with-azure-monitor-exporters).</sub>


