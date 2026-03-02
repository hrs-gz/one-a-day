import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  favoriteLead,
  generateLead,
  getLeadById,
  getLeads,
  getLeadsByDate,
  getTodayLead,
  voteOnLead,
} from "../api/leads";
import type { FavoritePayload, Lead, PaginatedResponse, VotePayload } from "../types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const leadKeys = {
  all: ["leads"] as const,
  today: () => [...leadKeys.all, "today"] as const,
  byDate: (date: string) => [...leadKeys.all, "byDate", date] as const,
  lists: () => [...leadKeys.all, "list"] as const,
  list: (page: number, limit: number, sourceType?: string) =>
    [...leadKeys.lists(), { page, limit, sourceType }] as const,
  detail: (id: number) => [...leadKeys.all, "detail", id] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/** Fetch today's lead. Returns null if none has been generated. */
export function useTodayLead() {
  return useQuery<Lead | null>({
    queryKey: leadKeys.today(),
    queryFn: getTodayLead,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/** Fetch all leads for a given date (YYYY-MM-DD). Returns empty array if none. */
export function useLeadsByDate(date: string) {
  return useQuery<Lead[]>({
    queryKey: leadKeys.byDate(date),
    queryFn: () => getLeadsByDate(date),
    staleTime: 1000 * 60 * 5,
  });
}

/** Fetch a paginated list of past leads. */
export function useLeads(page = 1, limit = 20, sourceType?: string) {
  return useQuery<PaginatedResponse<Lead>>({
    queryKey: leadKeys.list(page, limit, sourceType),
    queryFn: () => getLeads(page, limit, sourceType),
  });
}

/** Fetch a single lead by ID. */
export function useLeadById(id: number) {
  return useQuery<Lead>({
    queryKey: leadKeys.detail(id),
    queryFn: () => getLeadById(id),
    enabled: id > 0,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Trigger the daily pipeline to generate today's leads (top 3). */
export function useGenerateLead() {
  const queryClient = useQueryClient();
  return useMutation<Lead[], Error>({
    mutationFn: generateLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.today() });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
}

/** Vote on a lead with optimistic update. */
export function useVoteLead(date: string) {
  const queryClient = useQueryClient();
  return useMutation<Lead, Error, { id: number } & VotePayload>({
    mutationFn: ({ id, vote }) => voteOnLead(id, { vote }),
    onMutate: async ({ id, vote }) => {
      // Cancel in-flight refetches
      await queryClient.cancelQueries({ queryKey: leadKeys.byDate(date) });
      const previous = queryClient.getQueryData<Lead[]>(leadKeys.byDate(date));

      // Optimistic update
      if (previous) {
        queryClient.setQueryData<Lead[]>(
          leadKeys.byDate(date),
          previous.map((l) => (l.id === id ? { ...l, vote: vote as -1 | 0 | 1 } : l))
        );
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back on error
      const ctx = context as { previous?: Lead[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData(leadKeys.byDate(date), ctx.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.byDate(date) });
    },
  });
}

/** Toggle favorite on a lead with optimistic update. */
export function useFavoriteLead(date: string) {
  const queryClient = useQueryClient();
  return useMutation<Lead, Error, { id: number } & FavoritePayload>({
    mutationFn: ({ id, favorited }) => favoriteLead(id, { favorited }),
    onMutate: async ({ id, favorited }) => {
      await queryClient.cancelQueries({ queryKey: leadKeys.byDate(date) });
      const previous = queryClient.getQueryData<Lead[]>(leadKeys.byDate(date));

      if (previous) {
        queryClient.setQueryData<Lead[]>(
          leadKeys.byDate(date),
          previous.map((l) => (l.id === id ? { ...l, favorited } : l))
        );
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      const ctx = context as { previous?: Lead[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData(leadKeys.byDate(date), ctx.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.byDate(date) });
    },
  });
}
