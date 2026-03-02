import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createInterest,
  deleteInterest,
  getInterests,
  updateInterest,
} from "../api/interests";
import { createSource, deleteSource, getSources, toggleSource, updateSource } from "../api/sources";
import type {
  CreateInterestPayload,
  CreateSourcePayload,
  InterestConfig,
  PaginatedResponse,
  ScraperSource,
  UpdateInterestPayload,
  UpdateSourcePayload,
} from "../types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const interestKeys = {
  all: ["interests"] as const,
  lists: () => [...interestKeys.all, "list"] as const,
};

export const sourceKeys = {
  all: ["sources"] as const,
  lists: () => [...sourceKeys.all, "list"] as const,
};

// ---------------------------------------------------------------------------
// Interest queries + mutations
// ---------------------------------------------------------------------------

export function useInterests() {
  return useQuery<PaginatedResponse<InterestConfig>>({
    queryKey: interestKeys.lists(),
    queryFn: getInterests,
  });
}

export function useCreateInterest() {
  const queryClient = useQueryClient();
  return useMutation<InterestConfig, Error, CreateInterestPayload>({
    mutationFn: createInterest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: interestKeys.lists() });
    },
  });
}

export function useUpdateInterest() {
  const queryClient = useQueryClient();
  return useMutation<InterestConfig, Error, { id: number; payload: UpdateInterestPayload }>({
    mutationFn: ({ id, payload }) => updateInterest(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: interestKeys.lists() });
    },
  });
}

export function useDeleteInterest() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteInterest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: interestKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// Source queries + mutations
// ---------------------------------------------------------------------------

export function useSources() {
  return useQuery<PaginatedResponse<ScraperSource>>({
    queryKey: sourceKeys.lists(),
    queryFn: getSources,
  });
}

export function useToggleSource() {
  const queryClient = useQueryClient();
  return useMutation<ScraperSource, Error, { id: number; enabled: boolean }>({
    mutationFn: ({ id, enabled }) => toggleSource(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  return useMutation<ScraperSource, Error, CreateSourcePayload>({
    mutationFn: createSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

export function useUpdateSource() {
  const queryClient = useQueryClient();
  return useMutation<ScraperSource, Error, { id: number; payload: UpdateSourcePayload }>({
    mutationFn: ({ id, payload }) => updateSource(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}
