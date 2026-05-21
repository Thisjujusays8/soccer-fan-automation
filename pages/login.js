export default function Login({ error }) {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', maxWidth: 500, margin: '80px auto', padding: 20 }}>
      <h1>Dashboard login</h1>
      <p>Enter the dashboard password.</p>
      {error ? <p style={{ color: '#b00020' }}>Wrong password.</p> : null}
      <form method="post" action="/api/login">
        <input name="password" type="password" placeholder="Password" style={{ width: '100%', padding: 12, marginBottom: 12 }} />
        <button type="submit">Log in</button>
      </form>
    </main>
  );
}

export async function getServerSideProps(context) {
  return { props: { error: context.query.error === '1' } };
}
