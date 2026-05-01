/**Capacitor native shell config — iOS + Android wrapper for Meridian.**/
import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'ai.meridianpos.app',
  appName: 'Meridian',
  webDir: 'dist',
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#0A0A0B',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
    },
    StatusBar: {
      style: 'DARK' as any,
      backgroundColor: '#0A0A0B',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    Keyboard: {
      resize: 'body' as any,
      style: 'DARK' as any,
    },
    Camera: {
      presentationStyle: 'fullscreen' as any,
    },
    Haptics: {},
  },
  ios: {
    scheme: 'Meridian',
    contentInset: 'automatic',
  },
  android: {
    allowMixedContent: false,
    backgroundColor: '#0A0A0B',
  },
}

export default config
