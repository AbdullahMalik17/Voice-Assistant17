# Frontend Authentication Setup

## 1. Install Dependencies

```bash
cd web

# Install NextAuth and Supabase
npm install next-auth @supabase/supabase-js

# Install types
npm install --save-dev @types/next-auth
```

## 2. Create Environment Variables

Create `web/.env.local`:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-this-with-openssl-rand-base64-32

# For Supabase admin operations (optional - use anon key if not available)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

### Generate NEXTAUTH_SECRET

```bash
openssl rand -base64 32
```

## 3. Wrap App with SessionProvider

Update `web/src/app/layout.tsx`:

```typescript
import { SessionProvider } from '@/components/auth/SessionProvider';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
```

## 4. Protect Routes with Middleware

Create `web/src/middleware.ts`:

```typescript
export { default } from 'next-auth/middleware';

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * 1. /api routes
     * 2. /_next (Next.js internals)
     * 3. /auth/* (authentication pages)
     * 4. /favicon.ico, /robots.txt (static files)
     */
    '/((?!api|_next|auth|favicon.ico|robots.txt).*)',
  ],
};
```

## 5. Update Main Page to Check Auth

Update `web/src/app/page.tsx`:

```typescript
'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { ChatContainer } from '@/components/chat/ChatContainer';

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login');
    }
  }, [status, router]);

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return <ChatContainer />;
}
```

## 6. Add User Menu to Header

Update `web/src/components/chat/ChatContainer.tsx` to add user menu:

```typescript
import { useSession, signOut } from 'next-auth/react';

// Inside ChatContainer component:
const { data: session } = useSession();

// Add user menu button in header:
<div className="flex items-center gap-2">
  <span className="text-sm text-gray-600 dark:text-gray-300">
    {session?.user?.name}
  </span>
  <button
    onClick={() => signOut()}
    className="p-2 rounded-full glass hover:bg-white/10 dark:hover:bg-neon-blue/10"
  >
    <LogOut className="w-5 h-5" />
  </button>
</div>
```

## 7. Test Authentication Flow

### Register New User

1. Start dev server: `npm run dev`
2. Go to http://localhost:3000/auth/register
3. Fill in:
   - Display Name: Test User
   - Email: test@example.com
   - Password: password123
4. Click "Create account"
5. Check Supabase dashboard for new user

### Login

1. Go to http://localhost:3000/auth/login
2. Enter credentials
3. Click "Sign in"
4. Should redirect to main chat interface

### Verify Session

```typescript
// In any component:
import { useSession } from 'next-auth/react';

const { data: session } = useSession();
console.log('User:', session?.user);
console.log('Access Token:', session?.accessToken);
```

## 8. Pass JWT Token to Backend

Update `web/src/hooks/useWebSocket.ts` to send JWT:

```typescript
import { useSession } from 'next-auth/react';

export function useWebSocket(options: UseWebSocketOptions) {
  const { data: session } = useSession();

  useEffect(() => {
    if (!session?.accessToken) return;

    // Add token to WebSocket connection
    const wsUrl = `${url}?token=${session.accessToken}`;
    const ws = new WebSocket(wsUrl);

    // Rest of WebSocket logic...
  }, [session?.accessToken]);
}
```

## 9. Update API Calls with Auth Header

Update `web/src/components/chat/ConversationHistory.tsx`:

```typescript
import { useSession } from 'next-auth/react';

const { data: session } = useSession();

const fetchConversations = async () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(`${apiUrl}/api/conversations`, {
    headers: {
      'Authorization': `Bearer ${session?.accessToken}`,
    },
  });
  // ...
};
```

## 10. Troubleshooting

### Issue: NEXTAUTH_URL error

```
Error: Please define NEXTAUTH_URL environment variable
```

**Solution:**
Add to `.env.local`:
```bash
NEXTAUTH_URL=http://localhost:3000
```

### Issue: Session not persisting

**Solution:**
1. Check that SessionProvider wraps your app
2. Verify NEXTAUTH_SECRET is set
3. Clear browser cookies and try again

### Issue: Supabase connection error

**Solution:**
1. Verify NEXT_PUBLIC_SUPABASE_URL is correct
2. Check NEXT_PUBLIC_SUPABASE_ANON_KEY is valid
3. Test Supabase connection:

```typescript
import { supabase } from '@/lib/supabase/client';

const { data, error } = await supabase.auth.getSession();
console.log('Session:', data, error);
```

## 11. Files Created

- ✅ `web/src/lib/auth.ts` - NextAuth configuration
- ✅ `web/src/lib/supabase/client.ts` - Supabase client utils
- ✅ `web/src/app/api/auth/[...nextauth]/route.ts` - NextAuth API route
- ✅ `web/src/app/auth/login/page.tsx` - Login page
- ✅ `web/src/app/auth/register/page.tsx` - Register page
- ✅ `web/src/app/auth/error/page.tsx` - Error page
- ✅ `web/src/components/auth/SessionProvider.tsx` - Session wrapper
- ✅ `web/src/types/next-auth.d.ts` - Type definitions

## 12. Next Steps

1. ✅ Run `npm install` to install dependencies
2. ✅ Create `.env.local` with all environment variables
3. ✅ Update root layout with SessionProvider
4. ✅ Test registration and login flow
5. ⏭️ Implement backend JWT validation (next section)

**Continue to:** Backend JWT Validation Setup
