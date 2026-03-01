import { json } from '@sveltejs/kit';
import { getZoneSummary } from '$lib/map/mockData';

export const GET = async ({ params }) => {
  const citySlug = params.city;
  const summary = getZoneSummary(citySlug);
  return json(summary, {
    headers: {
      'cache-control': 'public, max-age=120'
    }
  });
};
