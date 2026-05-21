import { requestIsAuthed } from '../lib/dashboardAuth';
import { supabaseGet } from '../lib/supabaseRest';

const PLAYERS = [
  { slug: 'all', name: 'All players' },
  { slug: 'cherki', name: 'Rayan Cherki' },
  { slug: 'bellingham', name: 'Jude Bellingham' },
  { slug: 'yamal', name: 'Lamine Yamal' }
];

const STATUSES = ['found', 'approved', 'processed', 'failed', 'rejected', 'posted'];

function actionButton(id, status, label) {
  return (
    <form method="post" action={`/api/candidates/${id}`} style={{ display: 'inline' }}>
      <input type="hidden" name="status" value={status} />
      <button type="submit">{label}</button>
    </form>
  );
}

function CandidateCard({ candidate }) {
  return (
    <article style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16, marginBottom: 14 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 16 }}>
        <div>
          <h2 style={{ margin: '0 0 8px' }}>{candidate.title}</h2>
          <p style={{ margin: '4px 0' }}>Player: <strong>{candidate.player_slug}</strong></p>
          <p style={{ margin: '4px 0' }}>Status: <strong>{candidate.status}</strong></p>
          <p style={{ margin: '4px 0' }}>Score: <strong>{candidate.score}</strong></p>
          {candidate.error_message ? <p style={{ color: '#b00020' }}>Error: {candidate.error_message}</p> : null}
          <p><a href={candidate.source_url} target="_blank" rel="noreferrer">Open source</a></p>
          {candidate.video_url ? <p><a href={candidate.video_url} target="_blank" rel="noreferrer">Open processed video</a></p> : null}
        </div>
        {candidate.video_url ? (
          <video controls src={candidate.video_url} style={{ width: 220, maxWidth: '100%' }} />
        ) : null}
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        {candidate.status !== 'approved' ? actionButton(candidate.id, 'approved', 'Approve') : null}
        {candidate.status !== 'rejected' ? actionButton(candidate.id, 'rejected', 'Reject') : null}
        {candidate.status === 'failed' ? actionButton(candidate.id, 'found', 'Reset to found') : null}
        {candidate.status === 'processed' ? actionButton(candidate.id, 'approved', 'Reprocess') : null}
      </div>
    </article>
  );
}

export default function Home({ candidates, selectedPlayer, selectedStatus, error }) {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', maxWidth: 1100, margin: '32px auto', padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
        <div>
          <h1>Soccer Content Queue</h1>
          <p>Review clips before they are processed or posted. Keep auto approval off until the queue is consistently good.</p>
        </div>
        <a href="/api/logout">Log out</a>
      </div>

      <form method="get" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        <label>
          Player<br />
          <select name="player" defaultValue={selectedPlayer}>
            {PLAYERS.map(player => <option key={player.slug} value={player.slug}>{player.name}</option>)}
          </select>
        </label>
        <label>
          Status<br />
          <select name="status" defaultValue={selectedStatus}>
            {STATUSES.map(status => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <button type="submit" style={{ alignSelf: 'end' }}>Filter</button>
      </form>

      {error ? <p style={{ color: '#b00020' }}>{error}</p> : null}
      {!error && candidates.length === 0 ? <p>No candidates found for this filter.</p> : null}
      {candidates.map(candidate => <CandidateCard key={candidate.id} candidate={candidate} />)}
    </main>
  );
}

export async function getServerSideProps(context) {
  if (!requestIsAuthed(context.req)) {
    return {
      redirect: {
        destination: '/login',
        permanent: false
      }
    };
  }

  const selectedPlayer = context.query.player || 'all';
  const selectedStatus = context.query.status || 'found';
  const filters = [];

  if (selectedPlayer !== 'all') {
    filters.push(`player_slug=eq.${encodeURIComponent(selectedPlayer)}`);
  }
  filters.push(`status=eq.${encodeURIComponent(selectedStatus)}`);
  filters.push('select=id,player_slug,title,score,status,source_url,video_url,error_message,created_at');
  filters.push('order=created_at.desc');
  filters.push('limit=50');

  try {
    const candidates = await supabaseGet('clip_candidates', filters.join('&'));
    return { props: { candidates, selectedPlayer, selectedStatus, error: null } };
  } catch (error) {
    return { props: { candidates: [], selectedPlayer, selectedStatus, error: error.message } };
  }
}
