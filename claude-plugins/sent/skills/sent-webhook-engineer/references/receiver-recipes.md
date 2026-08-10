# Webhook receiver recipes by framework

Every recipe follows the same four steps: read the raw body, verify the signature and timestamp, acknowledge with `200`, then process asynchronously. Only the raw-body accessor and the background mechanism change.

## Table of contents

- [Raw-body accessor matrix](#raw-body-accessor-matrix)
- [Node and TypeScript](#node-and-typescript)
- [Python](#python)
- [Go](#go)
- [Java and Spring Boot](#java-and-spring-boot)
- [PHP](#php)
- [Ruby](#ruby)
- [ASP.NET Core](#aspnet-core)
- [Deployment traps](#deployment-traps)

## Raw-body accessor matrix

| Framework | Accessor | Trap that breaks the signature |
| --- | --- | --- |
| Next.js route handler | `await request.text()` | Keep the route on the Node runtime; do not re-parse the body first |
| Express | `express.raw({ type: 'application/json' })` on the webhook path | A global `express.json()` replaces the exact bytes |
| NestJS | `req.rawBody` | Requires `NestFactory.create(AppModule, { rawBody: true })` |
| FastAPI | `await request.body()` | Binding a Pydantic model first re-serializes |
| Django | `request.body` | Middleware that consumes the stream before the view |
| Flask | `request.get_data()` | `request.get_json()` first loses byte fidelity |
| Gin | `io.ReadAll(c.Request.Body)` | Body must be restored if later handlers read it |
| Echo | `io.ReadAll(c.Request().Body)` | Same |
| Spring Boot | `@RequestBody String payload` | Binding to a DTO re-serializes |
| Laravel | `$request->getContent()` | Middleware ordering; verify before any transform |
| Symfony | `$request->getContent()` | Same |
| Rails | `request.body.read` then `request.body.rewind` | `params` re-encodes the payload |
| Sinatra | `request.body.read` then `request.body.rewind` | Same |
| ASP.NET Core | `new StreamReader(request.Body).ReadToEndAsync()` | Read before model binding touches the stream |

Environment variables: the SDKs read `SENT_DM_API_KEY` by default, and the receiver samples use `SENT_DM_WEBHOOK_SECRET`. Older documentation pages use `SENT_API_KEY` and `SENT_WEBHOOK_SECRET`; treat those as aliases and standardize on the `SENT_DM_` names in new code.

## Node and TypeScript

```ts
import crypto from "node:crypto";

const TOLERANCE_SECONDS = 300;

export function verify(rawBody: string, webhookId: string, timestamp: string, header: string): boolean {
  const secret = process.env.SENT_DM_WEBHOOK_SECRET ?? "";
  if (!secret || !header?.startsWith("v1,")) return false;
  if (Math.abs(Math.floor(Date.now() / 1000) - Number(timestamp)) > TOLERANCE_SECONDS) return false;

  const key = Buffer.from(secret.replace(/^whsec_/, ""), "base64");
  const digest = crypto.createHmac("sha256", key).update(`${webhookId}.${timestamp}.${rawBody}`).digest("base64");
  const expected = Buffer.from(`v1,${digest}`);
  const received = Buffer.from(header);
  return expected.length === received.length && crypto.timingSafeEqual(expected, received);
}
```

Next.js route handler, kept on the Node runtime:

```ts
export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const rawBody = await request.text();
  const ok = verify(
    rawBody,
    request.headers.get("x-webhook-id") ?? "",
    request.headers.get("x-webhook-timestamp") ?? "",
    request.headers.get("x-webhook-signature") ?? "",
  );
  if (!ok) return new Response("invalid signature", { status: 401 });

  await enqueue(JSON.parse(rawBody));       // hand off, do not process inline
  return new Response(null, { status: 200 });
}
```

Express, scoping the raw parser to the webhook path only:

```js
app.post("/webhooks/sent", express.raw({ type: "application/json" }), (req, res) => {
  const rawBody = req.body.toString("utf8");
  if (!verify(rawBody, req.get("x-webhook-id"), req.get("x-webhook-timestamp"), req.get("x-webhook-signature"))) {
    return res.status(401).send("invalid signature");
  }
  res.status(200).end();
  queue.add("sent-event", JSON.parse(rawBody));   // after the response
});
```

Mount `express.json()` on other routers rather than globally with `app.use`. In NestJS create the app with `{ rawBody: true }` and read `req.rawBody`. Use BullMQ or an equivalent queue for the background step.

## Python

```python
import base64, hashlib, hmac, os, time

TOLERANCE_SECONDS = 300


def verify(raw_body: bytes, webhook_id: str, timestamp: str, header: str) -> bool:
    secret = os.environ.get("SENT_DM_WEBHOOK_SECRET", "")
    if not secret or not header.startswith("v1,"):
        return False
    try:
        if abs(int(time.time()) - int(timestamp)) > TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{webhook_id}.{timestamp}.".encode() + raw_body
    expected = "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(expected, header)
```

FastAPI:

```python
@app.post("/webhooks/sent", status_code=200)
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not verify(raw, request.headers.get("x-webhook-id", ""),
                  request.headers.get("x-webhook-timestamp", ""),
                  request.headers.get("x-webhook-signature", "")):
        raise HTTPException(status_code=401, detail="invalid signature")
    background.add_task(process_event, json.loads(raw))
    return {"received": True}
```

Django reads `request.body` in the view and must exempt the route from CSRF. Flask reads `request.get_data()` in a decorator that wraps the view. For anything slower than a database insert, hand the parsed event to Celery with `process_event.delay(event)` and route message traffic to a dedicated queue so bulk campaigns cannot starve transactional work.

## Go

```go
func Verify(rawBody []byte, webhookID, timestamp, header string) bool {
    secret := os.Getenv("SENT_DM_WEBHOOK_SECRET")
    if secret == "" || !strings.HasPrefix(header, "v1,") {
        return false
    }
    sentAt, err := strconv.ParseInt(timestamp, 10, 64)
    if err != nil || math.Abs(float64(time.Now().Unix()-sentAt)) > 300 {
        return false
    }
    key, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(secret, "whsec_"))
    if err != nil {
        return false
    }
    mac := hmac.New(sha256.New, key)
    mac.Write([]byte(webhookID + "." + timestamp + "."))
    mac.Write(rawBody)
    expected := "v1," + base64.StdEncoding.EncodeToString(mac.Sum(nil))
    return subtle.ConstantTimeCompare([]byte(expected), []byte(header)) == 1
}
```

In Gin read with `io.ReadAll(c.Request.Body)`; in Echo use `c.Request().Body`. If any later middleware needs the body, restore it with `c.Request.Body = io.NopCloser(bytes.NewBuffer(raw))`. Acknowledge, then dispatch to a goroutine with a bounded worker pool or a durable queue, and drain in-flight work on shutdown.

## Java and Spring Boot

```java
@PostMapping("/webhooks/sent")
public ResponseEntity<Void> receive(
        @RequestBody String payload,
        @RequestHeader("x-webhook-id") String webhookId,
        @RequestHeader("x-webhook-timestamp") String timestamp,
        @RequestHeader("x-webhook-signature") String signature) throws Exception {

    if (!WebhookSignature.verify(payload, webhookId, timestamp, signature)) {
        return ResponseEntity.status(401).build();
    }
    events.submit(payload);                    // @Async executor
    return ResponseEntity.ok().build();
}
```

Bind the body as `String`, never as a DTO, because Jackson re-serialization changes the bytes. Verify with `Mac.getInstance("HmacSHA256")` and compare using `MessageDigest.isEqual`. Push processing onto a `ThreadPoolTaskExecutor` or a broker.

## PHP

Laravel middleware runs before the controller and reads `$request->getContent()`:

```php
public function handle(Request $request, Closure $next)
{
    $secret = env('SENT_DM_WEBHOOK_SECRET', '');
    $signed = $request->header('x-webhook-id') . '.' . $request->header('x-webhook-timestamp') . '.' . $request->getContent();
    $key = base64_decode(preg_replace('/^whsec_/', '', $secret));
    $expected = 'v1,' . base64_encode(hash_hmac('sha256', $signed, $key, true));

    if (abs(time() - (int) $request->header('x-webhook-timestamp')) > 300
        || !hash_equals($expected, (string) $request->header('x-webhook-signature'))) {
        abort(401);
    }
    return $next($request);
}
```

Dispatch a `ShouldQueue` job from the controller. Symfony follows the same pattern with `$request->getContent()` and a Messenger message consumed by `messenger:consume`.

## Ruby

```ruby
def verified?(request)
  raw = request.body.read
  request.body.rewind
  secret = ENV.fetch("SENT_DM_WEBHOOK_SECRET", "")
  timestamp = request.get_header("HTTP_X_WEBHOOK_TIMESTAMP").to_s
  return false if secret.empty? || (Time.now.to_i - timestamp.to_i).abs > 300

  key = Base64.decode64(secret.delete_prefix("whsec_"))
  signed = "#{request.get_header('HTTP_X_WEBHOOK_ID')}.#{timestamp}.#{raw}"
  expected = "v1,#{Base64.strict_encode64(OpenSSL::HMAC.digest('SHA256', key, signed))}"
  ActiveSupport::SecurityUtils.secure_compare(expected, request.get_header("HTTP_X_WEBHOOK_SIGNATURE").to_s)
end
```

In Rails put this in a controller concern, skip `verify_authenticity_token` for the action, and enqueue with ActiveJob. In Sinatra read the body in the route and enqueue with Sidekiq; remember the client is memoized per Puma worker process.

## ASP.NET Core

```csharp
app.MapPost("/webhooks/sent", async (HttpRequest request) =>
{
    using var reader = new StreamReader(request.Body);
    var rawBody = await reader.ReadToEndAsync();

    if (!WebhookSignature.Verify(
            rawBody,
            request.Headers["x-webhook-id"],
            request.Headers["x-webhook-timestamp"],
            request.Headers["x-webhook-signature"],
            Environment.GetEnvironmentVariable("SENT_DM_WEBHOOK_SECRET")))
    {
        return Results.Unauthorized();
    }

    await channel.Writer.WriteAsync(rawBody);   // BackgroundService consumer
    return Results.Ok();
});
```

Read the stream before model binding touches it, compare with `CryptographicOperations.FixedTimeEquals`, and consume from a `BackgroundService`.

## Deployment traps

Reverse proxies and API gateways that buffer, recompress, or normalize request bodies break the signature; configure pass-through for the webhook path. Serverless platforms that hand the body as base64 require decoding to the original bytes before verification, not after. Load balancer idle timeouts shorter than `timeout_seconds` produce phantom failures that appear in the delivery log as timeouts with no `http_status_code`. Container clocks must be NTP-synchronized or the 300-second window rejects valid traffic. Finally, keep the webhook path out of user-auth middleware. If abuse controls are needed, apply signature-aware, capacity-safe controls rather than a generic pre-verification limiter that manufactures the consecutive failures leading to auto-disable.
