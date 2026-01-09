# Supabase Authentication Setup Guide

This guide will help you set up Supabase authentication for the Voice Assistant web application.

## Prerequisites

- A Supabase account (sign up at https://supabase.com)
- Your Supabase project URL and anon key (already in your `.env.local`)

## Step 1: Run the Database Migration

You need to create the `user_profiles` table in your Supabase database.

### Option A: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Click **"New Query"**
4. Copy the entire contents of `supabase/migrations/001_initial_schema.sql`
5. Paste it into the SQL editor
6. Click **"Run"** to execute the migration
7. You should see a success message

### Option B: Using Supabase CLI

If you have the Supabase CLI installed:

```bash
cd D:\Voice_Assistant\web
supabase db push
```

## Step 2: Configure Supabase Authentication Settings

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Settings**
3. Update the following settings:

### Email Authentication Settings

- **Enable Email Signup**: ✅ **Enabled**
- **Confirm email**: ❌ **Disabled** (for development)
  - For production, you should enable this and configure email templates
- **Secure email change**: ✅ **Enabled**

### Email Templates (Optional, for Production)

If you enable email confirmation, configure the email templates:
- Go to **Authentication** → **Email Templates**
- Customize the **Confirm Signup** template
- Set the confirmation URL to: `{{NEXTAUTH_URL}}/auth/confirm?token={{.Token}}`

### Password Requirements

- **Minimum password length**: 8 characters (already enforced in the app)

## Step 3: Verify the Setup

### Test the Database Migration

1. Go to **Table Editor** in Supabase dashboard
2. You should see a `user_profiles` table with the following columns:
   - `id` (uuid, primary key)
   - `user_id` (uuid, unique, references auth.users)
   - `display_name` (text)
   - `avatar_url` (text)
   - `preferences` (jsonb)
   - `metadata` (jsonb)
   - `created_at` (timestamp)
   - `updated_at` (timestamp)

### Test the Trigger

1. Go to **Database** → **Functions** in Supabase dashboard
2. You should see a function named `handle_new_user`
3. Go to **Database** → **Triggers**
4. You should see a trigger named `on_auth_user_created` on the `auth.users` table

## Step 4: Test Authentication

### Test Sign Up

1. Start your development server:
   ```bash
   npm run dev
   ```

2. Navigate to http://localhost:3000/auth/register

3. Create a new account with:
   - Display Name: Test User
   - Email: test@example.com
   - Password: password123

4. You should:
   - See a success message
   - Be automatically logged in (or redirected to login if email confirmation is enabled)
   - Have a profile automatically created in `user_profiles` table

### Test Sign In

1. Navigate to http://localhost:3000/auth/login

2. Sign in with the credentials you just created

3. You should be redirected to the home page

### Verify Profile Creation

1. Go to Supabase dashboard → **Table Editor** → `user_profiles`
2. You should see your test user's profile with the display name you entered

## Common Issues and Solutions

### Issue: "Supabase is not configured" error

**Solution**: Check that your `.env.local` file has the correct values:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
NEXTAUTH_SECRET=your-nextauth-secret
```

### Issue: "Invalid credentials" on sign up

**Solution**: This usually means:
1. The database migration hasn't been run
2. Email confirmation is required but not handled
3. Check the browser console for detailed error messages

### Issue: Sign up works but auto-login fails

**Solution**: This is usually because:
1. Email confirmation is enabled in Supabase settings
2. The profile wasn't created automatically

To fix: Disable "Confirm email" in Supabase Authentication settings for development.

### Issue: "relation 'user_profiles' does not exist"

**Solution**: The database migration hasn't been run. Follow Step 1 again.

### Issue: Profile is not created automatically

**Solution**:
1. Check that the trigger `on_auth_user_created` exists in your database
2. Verify the function `handle_new_user` exists
3. The updated `auth.ts` file now creates profiles as a fallback if they don't exist

## Security Notes

### For Development

- Email confirmation is disabled for easier testing
- Using localhost URLs

### For Production

1. **Enable email confirmation**:
   - Go to Authentication → Settings
   - Enable "Confirm email"
   - Configure email templates

2. **Update environment variables**:
   ```env
   NEXTAUTH_URL=https://your-production-domain.com
   ```

3. **Enable additional security features**:
   - Rate limiting
   - CAPTCHA for sign up
   - Email rate limiting

4. **Review Row Level Security (RLS) policies**:
   - The migration includes basic RLS policies
   - Review and adjust based on your needs

## Monitoring

### Check Authentication Logs

1. Go to **Authentication** → **Users** to see all registered users
2. Check **Logs** in the sidebar for authentication events and errors

### Database Logs

1. Go to **Logs** → **Database** to see database queries and errors
2. Useful for debugging profile creation issues

## Need Help?

If you continue to experience issues:

1. Check the browser console for JavaScript errors
2. Check the Network tab for failed API requests
3. Review Supabase logs for server-side errors
4. Ensure all environment variables are set correctly
5. Verify the database migration was successful

## What Was Fixed

The authentication issues were caused by:

1. **Missing database schema**: The `user_profiles` table didn't exist
2. **No automatic profile creation**: Profiles weren't created when users signed up
3. **Poor error handling**: The auth code didn't handle missing profiles gracefully

The fixes include:

1. ✅ Created database migration with `user_profiles` table
2. ✅ Added trigger to automatically create profiles on signup
3. ✅ Updated auth code to create profiles as fallback if they don't exist
4. ✅ Improved error handling and logging
5. ✅ Added comprehensive setup documentation
