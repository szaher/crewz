/**
 * Custom hook for managing slash commands in conversations
 * Fetches available prompt commands and handles autocomplete
 */

import { useState, useEffect, useCallback } from 'react';
import { promptApi, type CommandInfo } from '@/lib/api/prompts';

export function useSlashCommands() {
  const [commands, setCommands] = useState<CommandInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available commands
  const loadCommands = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await promptApi.listCommands();

      if (response.error) {
        throw new Error(response.error);
      }

      // Backend returns { commands: [...], total: N }
      // Extract the commands array
      const responseData = response.data as any;
      const commandsData = responseData?.commands || response.data || [];
      const commandsArray = Array.isArray(commandsData) ? commandsData : [];

      setCommands(commandsArray);
    } catch (err) {
      console.error('[useSlashCommands] Failed to load commands:', err);
      setError(err instanceof Error ? err.message : 'Failed to load commands');
      setCommands([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Filter commands based on input
  const filterCommands = useCallback((input: string): CommandInfo[] => {
    if (!input.startsWith('/')) {
      return [];
    }

    // Ensure commands is an array
    if (!Array.isArray(commands)) {
      return [];
    }

    const query = input.slice(1).toLowerCase(); // Remove '/' and lowercase

    if (!query) {
      // Show all commands if just '/'
      return commands;
    }

    // Filter by slug or name
    return commands.filter(cmd =>
      cmd.slug.toLowerCase().includes(query) ||
      cmd.name.toLowerCase().includes(query)
    );
  }, [commands]);

  // Get command by slug
  const getCommandBySlug = useCallback((slug: string): CommandInfo | undefined => {
    if (!Array.isArray(commands)) {
      return undefined;
    }
    return commands.find(cmd => cmd.slug === slug);
  }, [commands]);

  // Load commands on mount
  useEffect(() => {
    void loadCommands();
  }, [loadCommands]);

  return {
    commands,
    loading,
    error,
    filterCommands,
    getCommandBySlug,
    reload: loadCommands,
  };
}
