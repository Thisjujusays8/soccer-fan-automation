export default function Home() {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', maxWidth: 900, margin: '40px auto', padding: 20 }}>
      <h1>Soccer Content Queue</h1>
      <p>This dashboard is a placeholder. Use the queue script until the web approval UI is connected.</p>
      <h2>Current runs</h2>
      <ul>
        <li>cherki</li>
        <li>bellingham</li>
        <li>yamal</li>
      </ul>
      <h2>Approval flow</h2>
      <ol>
        <li>Run a workflow from GitHub Actions.</li>
        <li>Check Supabase clip_candidates.</li>
        <li>Approve a good clip.</li>
        <li>Run the workflow again to process it.</li>
      </ol>
    </main>
  );
}
