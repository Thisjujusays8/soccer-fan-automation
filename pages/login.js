import { makeAuthCookie, passwordMatches } from '../lib/dashboardAuth';

export default function Login({ error }) {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', maxWidth: 500, margin: '80px auto', padding: 20 }}>
      <h1>Dashboard login</h1>
      <p>Enter the dashboard password.</p>
      {error ? <p style={{ color: '#b00020' }}>{error}</p> : null}
      <form method="post">
        <input name="password" type="password" placeholder="Password" style={{ width: '100%', padding: 12, marginBottom: 12 }} />
        <button type="submit">Log in</button>
      </form>
    </main>
  );
}

export async function getServerSideProps(context) {
  if (context.req.method === 'POST') {
    const chunks = [];
    for await (const chunk of context.req) {
      chunks.push(chunk);
    }
    const body = Buffer.concat(chunks).toString('utf-8');
    const params = new URLSearchParams(body);
    const password = params.get('password') || '';

    if (passwordMatches(password)) {
      context.res.setHeader('Set-Cookie', makeAuthCookie());
      context.res.writeHead(303, { Location: '/' });
      context.res.end();
      return { props: {} };
    }

    return { props: { error: 'Wrong password.' } };
  }

  return { props: { error: null } };
}
