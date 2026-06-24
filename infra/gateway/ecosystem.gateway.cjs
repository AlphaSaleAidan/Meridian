// PM2 config for the Meridian streaming gateway — SEPARATE from the main
// ecosystem.config.js so deploying it never disturbs the running prod apps.
// Start (gated, on the box, only on Aidan's go):
//   pm2 start infra/gateway/ecosystem.gateway.cjs
//
// Requires the mediamtx + turnserver binaries installed and the env vars set
// (MERIDIAN_TURN_HOST/USER/PASS/SECRET, GATEWAY_INTERNAL_SECRET, external IP).
module.exports = {
  apps: [
    {
      name: 'meridian-gateway',
      script: 'mediamtx',
      args: 'infra/gateway/mediamtx.yml',
      cwd: '/root/Meridian',
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      max_memory_restart: '300M', // router is light; bandwidth is the real limit
      env: { MTX_CONFKEY: '' },
    },
    {
      name: 'meridian-turn',
      script: '/usr/bin/bash',
      args: "-c 'turnserver -c infra/gateway/turnserver.conf'",
      cwd: '/root/Meridian',
      exec_mode: 'fork',
      instances: 1,
      max_memory_restart: '200M',
    },
  ],
}
