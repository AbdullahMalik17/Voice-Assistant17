/**
 * Supabase Client for Browser
 * Use this in client components
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase = (supabaseUrl && supabaseAnonKey)
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      },
    })
  : null;

/**
 * Sign up a new user
 */
export async function signUp(email: string, password: string, displayName?: string) {
  if (!supabase) return { data: null, error: new Error('Supabase is not configured') };
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        display_name: displayName || email.split('@')[0],
      },
    },
  });

  return { data, error };
}

/**
 * Sign in existing user
 */
export async function signIn(email: string, password: string) {
  if (!supabase) return { data: null, error: new Error('Supabase is not configured') };
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  return { data, error };
}

/**
 * Sign out current user
 */
export async function signOut() {
  if (!supabase) return { error: new Error('Supabase is not configured') };
  const { error } = await supabase.auth.signOut();
  return { error };
}

/**
 * Get current session
 */
export async function getSession() {
  if (!supabase) return { data: null, error: new Error('Supabase is not configured') };
  const { data, error } = await supabase.auth.getSession();
  return { data, error };
}

/**
 * Get user profile
 */
export async function getUserProfile(userId: string) {
  if (!supabase) return { data: null, error: new Error('Supabase is not configured') };
  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .eq('user_id', userId)
    .single();

  return { data, error };
}

/**
 * Update user profile
 */
export async function updateUserProfile(
  userId: string,
  updates: {
    display_name?: string;
    avatar_url?: string;
    preferences?: Record<string, any>;
    metadata?: Record<string, any>;
  }
) {
  if (!supabase) return { data: null, error: new Error('Supabase is not configured') };
  const { data, error } = await supabase
    .from('user_profiles')
    .update(updates)
    .eq('user_id', userId)
    .select()
    .single();

  return { data, error };
}
