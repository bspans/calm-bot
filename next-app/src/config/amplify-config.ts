import { Amplify } from 'aws-amplify';

const isLocalhost = process.env.NEXT_PUBLIC_API_URL?.includes('localhost') || 
                   process.env.NEXT_PUBLIC_API_URL?.includes('127.0.0.1');

const localConfig = {
  Auth: {
    region: process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-1',
    userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID || 'local',
    userPoolWebClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || 'local',
    mandatorySignIn: true,
    oauth: {
      domain: process.env.NEXT_PUBLIC_AUTH_DOMAIN || 'localhost:3000',
      scope: ['email', 'profile', 'openid'],
      redirectSignIn: process.env.NEXT_PUBLIC_REDIRECT_SIGN_IN || 'http://localhost:3000',
      redirectSignOut: process.env.NEXT_PUBLIC_REDIRECT_SIGN_OUT || 'http://localhost:3000',
      responseType: 'code'
    }
  },
  API: {
    endpoints: [
      {
        name: 'CalmChatAPI',
        endpoint: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api',
        region: process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-1'
      }
    ]
  }
};

export const configureAmplify = () => {
  try {
    Amplify.configure(localConfig);
  } catch (error) {
    console.error('Error configuring Amplify:', error);
  }
};
