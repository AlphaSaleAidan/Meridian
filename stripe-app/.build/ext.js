var __StripeExtExports = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // .build/manifest.js
  var manifest_exports = {};
  __export(manifest_exports, {
    BUILD_TIME: () => BUILD_TIME,
    default: () => manifest_default
  });
  var BUILD_TIME = "2026-08-10 22:01:06.337324592 +0200 CEST m=+3.362082274";
  var manifest_default = {
    "$schema": "https://stripe.com/stripe-app.schema.json",
    "allowed_redirect_uris": [
      "https://api.meridian.tips/api/pos/stripe/callback"
    ],
    "distribution_type": "public",
    "icon": "./icon.png",
    "id": "tips.meridian.pos-analytics",
    "name": "Meridian POS Analytics",
    "permissions": [
      {
        "permission": "charge_read",
        "purpose": "Reads your charge and refund history to power Meridian's revenue analytics and reporting for your business."
      }
    ],
    "post_install_action": {
      "type": "external",
      "url": "https://meridian.tips/app/settings"
    },
    "sandbox_install_compatible": true,
    "stripe_api_access_type": "oauth",
    "version": "1.0.0"
  };
  return __toCommonJS(manifest_exports);
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsibWFuaWZlc3QuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbIi8vIEFVVE9HRU5FUkFURUQgLSBETyBOT1QgTU9ESUZZXG5cbi8vIFRpbWVzdGFtcCBjaGFuZ2VzIG9uIGV2ZXJ5IGV4cG9ydCwgZW5zdXJpbmcgdGhlIGRldiBzZXJ2ZXIgZGV0ZWN0cyBhIHJlYnVpbGRcbmV4cG9ydCBjb25zdCBCVUlMRF9USU1FID0gJzIwMjYtMDgtMTAgMjI6MDE6MDYuMzM3MzI0NTkyICswMjAwIENFU1QgbT0rMy4zNjIwODIyNzQnO1xuXG4vLyBBcHAgbWFuaWZlc3QgXHUyMDE0IGNvbnN1bWVkIGJ5IHRoZSBEYXNoYm9hcmQgdG8gY29uZmlndXJlIHRoZSBhcHBcbmV4cG9ydCBkZWZhdWx0IHtcbiAgXCIkc2NoZW1hXCI6IFwiaHR0cHM6Ly9zdHJpcGUuY29tL3N0cmlwZS1hcHAuc2NoZW1hLmpzb25cIixcbiAgXCJhbGxvd2VkX3JlZGlyZWN0X3VyaXNcIjogW1xuICAgIFwiaHR0cHM6Ly9hcGkubWVyaWRpYW4udGlwcy9hcGkvcG9zL3N0cmlwZS9jYWxsYmFja1wiXG4gIF0sXG4gIFwiZGlzdHJpYnV0aW9uX3R5cGVcIjogXCJwdWJsaWNcIixcbiAgXCJpY29uXCI6IFwiLi9pY29uLnBuZ1wiLFxuICBcImlkXCI6IFwidGlwcy5tZXJpZGlhbi5wb3MtYW5hbHl0aWNzXCIsXG4gIFwibmFtZVwiOiBcIk1lcmlkaWFuIFBPUyBBbmFseXRpY3NcIixcbiAgXCJwZXJtaXNzaW9uc1wiOiBbXG4gICAge1xuICAgICAgXCJwZXJtaXNzaW9uXCI6IFwiY2hhcmdlX3JlYWRcIixcbiAgICAgIFwicHVycG9zZVwiOiBcIlJlYWRzIHlvdXIgY2hhcmdlIGFuZCByZWZ1bmQgaGlzdG9yeSB0byBwb3dlciBNZXJpZGlhbidzIHJldmVudWUgYW5hbHl0aWNzIGFuZCByZXBvcnRpbmcgZm9yIHlvdXIgYnVzaW5lc3MuXCJcbiAgICB9XG4gIF0sXG4gIFwicG9zdF9pbnN0YWxsX2FjdGlvblwiOiB7XG4gICAgXCJ0eXBlXCI6IFwiZXh0ZXJuYWxcIixcbiAgICBcInVybFwiOiBcImh0dHBzOi8vbWVyaWRpYW4udGlwcy9hcHAvc2V0dGluZ3NcIlxuICB9LFxuICBcInNhbmRib3hfaW5zdGFsbF9jb21wYXRpYmxlXCI6IHRydWUsXG4gIFwic3RyaXBlX2FwaV9hY2Nlc3NfdHlwZVwiOiBcIm9hdXRoXCIsXG4gIFwidmVyc2lvblwiOiBcIjEuMC4wXCJcbn07XG4iXSwKICAibWFwcGluZ3MiOiAiOzs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFHTyxNQUFNLGFBQWE7QUFHMUIsTUFBTyxtQkFBUTtBQUFBLElBQ2IsV0FBVztBQUFBLElBQ1gseUJBQXlCO0FBQUEsTUFDdkI7QUFBQSxJQUNGO0FBQUEsSUFDQSxxQkFBcUI7QUFBQSxJQUNyQixRQUFRO0FBQUEsSUFDUixNQUFNO0FBQUEsSUFDTixRQUFRO0FBQUEsSUFDUixlQUFlO0FBQUEsTUFDYjtBQUFBLFFBQ0UsY0FBYztBQUFBLFFBQ2QsV0FBVztBQUFBLE1BQ2I7QUFBQSxJQUNGO0FBQUEsSUFDQSx1QkFBdUI7QUFBQSxNQUNyQixRQUFRO0FBQUEsTUFDUixPQUFPO0FBQUEsSUFDVDtBQUFBLElBQ0EsOEJBQThCO0FBQUEsSUFDOUIsMEJBQTBCO0FBQUEsSUFDMUIsV0FBVztBQUFBLEVBQ2I7IiwKICAibmFtZXMiOiBbXQp9Cg==
