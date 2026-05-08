/**
 * Fonoster Voice Application — receives inbound SIP calls and streams
 * audio to the Pipecat phone agent via WebSocket.
 *
 * This replaces Twilio's TwiML + <Connect><Stream> pattern.
 * Self-hosted via Fonoster + FreeSWITCH.
 */
const { VoiceServer } = require("@fonoster/voice");
const fetch = require("node-fetch");

const PIPECAT_WS_URL = process.env.PIPECAT_WS_URL || "ws://localhost:8090/ws";
const SUPABASE_URL = process.env.SUPABASE_URL || "";
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || "";

async function getMerchantIdByPhone(phoneNumber) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return "demo-merchant";
  }

  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/phone_agent_config?phone_number=eq.${encodeURIComponent(phoneNumber)}&select=merchant_id`,
      {
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
        },
      }
    );
    const data = await res.json();
    if (data && data.length > 0) {
      return data[0].merchant_id;
    }
  } catch (err) {
    console.error("Failed to lookup merchant:", err.message);
  }
  return null;
}

async function getMerchantConfig(merchantId) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return {
      active: true,
      business_name: "Demo Restaurant",
      business_hours: {},
      after_hours_message:
        "Thank you for calling. We are currently closed.",
    };
  }

  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/phone_agent_config?merchant_id=eq.${merchantId}&select=*`,
      {
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
        },
      }
    );
    const data = await res.json();
    return data && data.length > 0 ? data[0] : null;
  } catch (err) {
    console.error("Failed to load merchant config:", err.message);
    return null;
  }
}

function isWithinBusinessHours(config) {
  if (!config.business_hours || Object.keys(config.business_hours).length === 0) {
    return true;
  }

  const now = new Date();
  const dayNames = [
    "sunday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday",
  ];
  const dayName = dayNames[now.getDay()];
  const hours = config.business_hours[dayName];

  if (!hours || hours.closed) return false;

  const currentTime = now.toTimeString().slice(0, 5);
  return currentTime >= (hours.open || "00:00") && currentTime <= (hours.close || "23:59");
}

new VoiceServer().listen(async (req, voice) => {
  const { ingressNumber, sessionRef, callerNumber } = req;

  console.log(
    `Incoming call: from=${callerNumber} to=${ingressNumber} session=${sessionRef}`
  );

  await voice.answer();

  const merchantId = await getMerchantIdByPhone(ingressNumber);

  if (!merchantId) {
    await voice.say("Thank you for calling. This number is not configured.");
    await voice.hangup();
    return;
  }

  const config = await getMerchantConfig(merchantId);

  if (!config || !config.active) {
    await voice.say(
      "Thank you for calling. Phone orders are not available at this time."
    );
    await voice.hangup();
    return;
  }

  if (!isWithinBusinessHours(config)) {
    const msg =
      config.after_hours_message ||
      `Thank you for calling ${config.business_name}. We are currently closed.`;
    await voice.say(msg);
    await voice.hangup();
    return;
  }

  // Stream bidirectional audio to Pipecat via WebSocket
  await voice.stream({
    url: `${PIPECAT_WS_URL}/${merchantId}/${sessionRef}`,
  });
});
