import { useTranslation } from 'react-i18next';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { Database } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export function LoginPage() {
  const { t } = useTranslation();
  const { loginWithGoogle } = useAuth();

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      toast.error(t('auth.login_failed'));
      return;
    }
    try {
      await loginWithGoogle(credentialResponse.credential);
    } catch {
      toast.error(t('auth.login_failed'));
    }
  };

  const handleGoogleError = () => {
    toast.error(t('auth.google_error'));
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50">
      <Card className="w-full max-w-md mx-4 shadow-xl">
        <CardContent className="pt-8 pb-8 flex flex-col items-center space-y-6">
          <div className="flex items-center space-x-2">
            <Database className="w-10 h-10 text-blue-600" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              {t('app.title')}
            </h1>
          </div>
          <p className="text-slate-500 text-sm text-center">
            {t('auth.sign_in_prompt')}
          </p>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            size="large"
            width="300"
            theme="outline"
            text="signin_with"
          />
        </CardContent>
      </Card>
    </div>
  );
}
