/**
 * Sets up undici ProxyAgent for Node.js fetch in sandboxed environments.
 * Must be imported before any fetch calls.
 */
const proxyUrl = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;

if (proxyUrl) {
  try {
    const { ProxyAgent, setGlobalDispatcher } = require("undici");
    const agent = new ProxyAgent(proxyUrl);
    setGlobalDispatcher(agent);
    console.log("🌐 Proxy configured for Node.js fetch");
  } catch {
    console.log("⚠️ Could not configure proxy (undici not available)");
  }
}
