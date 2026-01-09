/**
 * NextAuth Configuration with Supabase
 */

import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Supabase',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Email and password required');
        }

        if (!supabaseUrl || !supabaseServiceKey) {
          throw new Error('Supabase configuration missing');
        }

        const supabase = createClient(supabaseUrl, supabaseServiceKey);

        // Sign in with Supabase
        const { data, error } = await supabase.auth.signInWithPassword({
          email: credentials.email,
          password: credentials.password,
        });

        if (error || !data.user) {
          throw new Error(error?.message || 'Invalid credentials');
        }

        // Fetch user profile
        const { data: profile } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', data.user.id)
          .single();

        return {
          id: data.user.id,
          email: data.user.email!,
          name: profile?.display_name || data.user.email!.split('@')[0],
          image: profile?.avatar_url,
          accessToken: data.session?.access_token,
          refreshToken: data.session?.refresh_token,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      // Initial sign in
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        token.picture = user.image;
        token.accessToken = (user as any).accessToken;
        token.refreshToken = (user as any).refreshToken;
      }

      return token;
    },
    async session({ session, token }) {
      if (token) {
        session.user.id = token.id as string;
        session.user.email = token.email as string;
        session.user.name = token.name as string;
        session.user.image = token.picture as string;
        (session as any).accessToken = token.accessToken;
        (session as any).refreshToken = token.refreshToken;
      }

      return session;
    },
  },
  pages: {
    signIn: '/auth/login',
    signOut: '/auth/login',
    error: '/auth/error',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  secret: process.env.NEXTAUTH_SECRET,
};
