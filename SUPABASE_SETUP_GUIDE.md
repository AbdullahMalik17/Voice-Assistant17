# Supabase Setup Guide

## 1. Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose organization or create new one
4. Enter project details:
   - **Name:** voice-assistant
   - **Database Password:** (Generate strong password - save it!)
   - **Region:** Choose closest to your users
5. Click "Create new project"
6. Wait 2-3 minutes for project to initialize

---

## 2. Get API Credentials

1. Go to **Project Settings** (gear icon in sidebar)
2. Click **API** section
3. Copy the following values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

---

## 3. Run Database Migrations

### Option A: Using Supabase SQL Editor (Recommended)

1. Go to **SQL Editor** in Supabase dashboard
2. Click **New query**
3. Copy and paste contents of `supabase/migrations/001_user_profiles.sql`
4. Click **Run** (or press Ctrl+Enter)
5. Repeat for `002_conversation_sessions.sql`
6. Repeat for `003_conversation_turns.sql`

### Option B: Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

---

## 4. Configure Email Authentication

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider
3. Configure email templates:
   - Go to **Email Templates**
   - Customize confirmation email (optional)

### SMTP Configuration (Optional)

For production, configure custom SMTP:

1. Go to **Project Settings** → **Authentication**
2. Scroll to **SMTP Settings**
3. Enter your SMTP details:
   - Host: `smtp.gmail.com` (or your provider)
   - Port: `587`
   - Username: your-email@gmail.com
   - Password: app-specific password

---

## 5. Verify Database Tables

1. Go to **Table Editor** in Supabase
2. Verify these tables exist:
   - ✅ `user_profiles`
   - ✅ `conversation_sessions`
   - ✅ `conversation_turns`

3. Check Row Level Security (RLS):
   - Click on each table
   - Click **Policies** tab
   - Verify policies are enabled

---

## 6. Test User Registration

### Using Supabase Dashboard

1. Go to **Authentication** → **Users**
2. Click **Add user** → **Create new user**
3. Enter email and password
4. Click **Create user**
5. Go to **Table Editor** → **user_profiles**
6. Verify a profile was auto-created for the user

---

## 7. Environment Variables

### Backend (.env)

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Existing variables
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
PICOVOICE_ACCESS_KEY=...
```

### Frontend (web/.env.local)

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret-generate-with-openssl

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

### Generate NextAuth Secret

```bash
openssl rand -base64 32
```

---

## 8. Verify Setup Checklist

- ✅ Supabase project created
- ✅ API credentials copied
- ✅ Database migrations run successfully
- ✅ Tables exist with RLS enabled
- ✅ Email authentication enabled
- ✅ Environment variables configured
- ✅ Test user created and profile auto-generated

---

## 9. Troubleshooting

### Issue: Migration fails with "permission denied"

**Solution:**
- Ensure you're using the SQL Editor with admin privileges
- Or use Supabase CLI with proper authentication

### Issue: User profile not auto-created

**Solution:**
```sql
-- Check if trigger exists
SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Manually create profile for existing users
INSERT INTO public.user_profiles (user_id, display_name)
SELECT id, split_part(email, '@', 1)
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM public.user_profiles);
```

### Issue: RLS blocking queries

**Solution:**
- Verify you're authenticated (check JWT token)
- Use service role key for backend operations
- Check RLS policies match your auth.uid()

---

## 10. Next Steps

Once Supabase is set up:
1. ✅ Install frontend dependencies
2. ✅ Configure NextAuth.js
3. ✅ Create authentication UI
4. ✅ Add JWT validation to backend
5. ✅ Test login/register flow

**Continue to next step:** Frontend Setup
