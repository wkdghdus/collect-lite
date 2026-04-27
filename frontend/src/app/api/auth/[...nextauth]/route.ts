import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email) return null;
        return { id: "1", name: "Demo User", email: credentials.email };
      },
    }),
  ],
  pages: { signIn: "/auth/signin" },
});

export { handler as GET, handler as POST };
