---
title: "NetSuite Integration"
description: "Integrate LintPDF with Oracle NetSuite via SuiteScript Restlets, SuiteFlow, or scheduled scripts."
section: "integrations"
order: 11
---

# NetSuite Integration

Oracle NetSuite is a cloud ERP commonly used by print, packaging, and label businesses for billing, inventory, and order management. NetSuite exposes extensibility through **SuiteScript** — JavaScript that runs server-side. The cleanest integration with LintPDF uses a **Restlet** (a publishable SuiteScript endpoint) plus a Scheduled or Map/Reduce script that invokes LintPDF when artwork is attached to a Sales Order, Work Order, or custom transaction record.

This is potentially the **easiest direct integration** of any ERP that doesn't expose a turnkey print workflow, because Restlets give you a customizable HTTP entry point on the NetSuite side and SuiteScript can call out to any HTTPS endpoint.

## Integration Architecture

```
┌──────────┐  Suitelet/Restlet  ┌──────────────┐  HTTP POST  ┌──────────┐
│ NetSuite │───────────────────→│  SuiteScript │────────────→│ LintPDF  │
│  ERP     │                    │  (server)    │             │ API      │
│          │◄───────────────────│              │◄────────────│          │
│          │   Field updates    │              │  Webhook    │          │
└──────────┘                    └──────────────┘             └──────────┘
```

## Option 1: SuiteScript + Restlet (Recommended)

The simplest production pattern is a **User Event Script** that fires when artwork is attached, invokes LintPDF via `https.post`, and writes the resulting findings back to a custom field on the originating record. A separate **Restlet** receives webhook callbacks from LintPDF when jobs complete asynchronously.

### Step 1: Create the Outbound Script

Add a User Event or Workflow Action Script (SuiteScript 2.x) on the Sales Order / Work Order / custom transaction:

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 */
define(["N/file", "N/https", "N/record", "N/runtime"], function (file, https, record, runtime) {

  function afterSubmit(context) {
    if (context.type !== context.UserEventType.EDIT) return;

    var rec = context.newRecord;
    var artworkFileId = rec.getValue({ fieldId: "custbody_artwork_file" });
    if (!artworkFileId) return;

    var pdf = file.load({ id: artworkFileId });
    var apiKey = runtime.getCurrentScript().getParameter({ name: "custscript_lintpdf_api_key" });

    var response = https.post({
      url: "https://api.lintpdf.com/api/v1/jobs",
      headers: {
        "Authorization": "Bearer " + apiKey,
      },
      body: {
        file: pdf,
        profile_id: "gwg-sheetfed",
        webhook_url: "https://" + runtime.getCurrentScript().getParameter({ name: "custscript_restlet_host" })
                     + "/app/site/hosting/restlet.nl?script=customscript_lintpdf_callback&deploy=1",
      },
    });

    var job = JSON.parse(response.body);
    record.submitFields({
      type: rec.type,
      id: rec.id,
      values: { custbody_lintpdf_job_id: job.id, custbody_lintpdf_status: "pending" },
    });
  }

  return { afterSubmit: afterSubmit };
});
```

### Step 2: Create the Callback Restlet

Publish a Restlet to receive webhook callbacks from LintPDF and update the originating transaction:

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 */
define(["N/record", "N/search"], function (record, search) {

  function post(payload) {
    // payload from LintPDF webhook: { event: "job.completed", job: { id, status, summary } }
    if (payload.event !== "job.completed") return { ok: true };

    var lintpdfJobId = payload.job.id;
    var passed = payload.job.summary && payload.job.summary.passed;

    var results = search.create({
      type: "salesorder",
      filters: [["custbody_lintpdf_job_id", "is", lintpdfJobId]],
      columns: ["internalid"],
    }).run().getRange({ start: 0, end: 1 });

    if (!results.length) return { ok: false, error: "no matching record" };

    record.submitFields({
      type: "salesorder",
      id: results[0].getValue("internalid"),
      values: {
        custbody_lintpdf_status: passed ? "pass" : "fail",
        custbody_lintpdf_findings: payload.job.summary.total_findings || 0,
      },
    });

    return { ok: true };
  }

  return { post: post };
});
```

### Step 3: Deploy and Configure

1. Upload both SuiteScripts to the **File Cabinet** (under SuiteScripts).
2. Create **Script Deployments** for each:
   - User Event Script: deploy on the Sales Order (or Work Order) record type
   - Restlet: note the **External URL** — this is what LintPDF posts the webhook to
3. Add the LintPDF API key as a **Script Parameter** (`custscript_lintpdf_api_key`) so it's not hard-coded.
4. Add the four custom fields used above (`custbody_artwork_file`, `custbody_lintpdf_job_id`, `custbody_lintpdf_status`, `custbody_lintpdf_findings`) via **Customization → Lists, Records, & Fields → Transaction Body Fields**.
5. Configure **Token-Based Authentication (TBA)** for the Restlet so LintPDF can post to it without an interactive login.

## Option 2: Polling Middleware (Outside NetSuite)

If you can't deploy SuiteScript at your site, a small middleware service can poll NetSuite via SuiteTalk REST and bridge to LintPDF:

```python
"""
NetSuite SuiteTalk REST -> LintPDF integration.

Authenticates against NetSuite using OAuth 1.0a Token-Based
Authentication (TBA), polls for transactions needing preflight,
submits artwork to LintPDF, writes results back via the SuiteTalk
REST record API.
"""

import httpx
import time
import logging
from requests_oauthlib import OAuth1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# ----- NetSuite SuiteTalk REST configuration -----
NS_ACCOUNT_ID = "1234567"
NS_BASE = f"https://{NS_ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/record/v1"
NS_AUTH = OAuth1(
    client_key="<consumer_key>",
    client_secret="<consumer_secret>",
    resource_owner_key="<token_id>",
    resource_owner_secret="<token_secret>",
    realm=NS_ACCOUNT_ID,
    signature_method="HMAC-SHA256",
)

# ----- LintPDF configuration -----
LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"


def fetch_pending_orders():
    """SuiteQL: pull orders flagged as needing preflight."""
    resp = httpx.post(
        f"https://{NS_ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql",
        json={"q": "SELECT id, custbody_artwork_url FROM transaction WHERE custbody_lintpdf_status = 'pending'"},
        auth=NS_AUTH,
        headers={"Prefer": "transient"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def preflight(lp: httpx.Client, pdf: bytes, filename: str) -> dict:
    resp = lp.post(
        "/api/v1/jobs",
        files={"file": (filename, pdf, "application/pdf")},
        data={"profile_id": LINTPDF_PROFILE},
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]

    for _ in range(120):
        time.sleep(5)
        resp = lp.get(f"/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data["status"] in ("complete", "failed"):
            return data

    raise TimeoutError(f"Job {job_id} timed out")


def update_order(order_id: str, result: dict):
    summary = result.get("summary", {})
    httpx.patch(
        f"{NS_BASE}/salesOrder/{order_id}",
        json={
            "custbody_lintpdf_status": "pass" if summary.get("passed") else "fail",
            "custbody_lintpdf_findings": summary.get("total_findings", 0),
        },
        auth=NS_AUTH,
        timeout=30,
    ).raise_for_status()


def main():
    lp = httpx.Client(
        base_url=LINTPDF_BASE,
        headers={"Authorization": f"Bearer {LINTPDF_API_KEY}"},
        timeout=60,
    )

    while True:
        try:
            for order in fetch_pending_orders():
                log.info("Processing NetSuite order: %s", order["id"])
                pdf = httpx.get(order["custbody_artwork_url"], timeout=60).content
                result = preflight(lp, pdf, f"{order['id']}.pdf")
                update_order(order["id"], result)
                log.info("Order %s: %s", order["id"], "PASS" if result["summary"]["passed"] else "FAIL")
        except Exception:
            log.exception("Error in polling loop")
        time.sleep(30)


if __name__ == "__main__":
    main()
```

## Comparison

| Approach                | Complexity      | Maintenance | Best For                                    |
| ----------------------- | --------------- | ----------- | ------------------------------------------- |
| SuiteScript + Restlet   | Medium (JS)     | Low         | Production, native NetSuite UX integration  |
| SuiteFlow + HTTPS       | Low (no-code)   | Low         | Simple flows, small teams                   |
| Polling middleware      | Medium (code)   | Medium      | Sites that can't deploy SuiteScript         |

## Tips

- **Token-Based Authentication (TBA):** SuiteTalk REST and Restlet endpoints both require TBA. Set up an Integration record under **Setup → Integration → Manage Integrations** and issue a token for the script user.
- **Webhooks beat polling:** Have LintPDF post to your Restlet on `job.completed` rather than polling from SuiteScript — it's cheaper on SuiteScript governance units and keeps NetSuite responsive.
- **Governance limits:** SuiteScript has per-script governance limits. Heavy submission workloads should be Map/Reduce scripts, not User Event scripts, so they don't block record saves.
- **File Cabinet vs. external storage:** Artwork attached to NetSuite via the File Cabinet can be loaded with `N/file`. If artwork lives in S3 / Azure Blob, fetch the URL and stream the bytes through `N/https.requestUrl` directly to LintPDF.
- **Sandbox first:** Always deploy and test integrations in a NetSuite Sandbox account before promoting to Production. SuiteScript bugs that mutate transactions can be hard to reverse.
