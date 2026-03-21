---
title: "Authentication"
description: "How to authenticate with the LintPDF API using Bearer tokens."
section: "core"
order: 2
---

# Authentication

Include your API Key in the `Authorization` header as a Bearer token:

```
Authorization: Bearer lpdf_your_api_key
```

> **Keep your API Key secret.** Never expose it in client-side code, public repositories, or browser requests. Use environment variables and server-side calls only.
