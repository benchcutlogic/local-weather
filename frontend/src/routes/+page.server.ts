import { CITIES } from '$lib/cities';

export const load = async () => {
  return { cities: CITIES };
};
