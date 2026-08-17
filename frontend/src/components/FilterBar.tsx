import { Select, SelectItem, Text } from "@tremor/react";

interface Props {
  teams: string[];
  developers: string[];
  selectedTeam: string;
  selectedDeveloper: string;
  selectedDate: string;
  onTeamChange: (team: string) => void;
  onDeveloperChange: (developer: string) => void;
  onDateChange: (date: string) => void;
}

export function FilterBar({
  teams,
  developers,
  selectedTeam,
  selectedDeveloper,
  selectedDate,
  onTeamChange,
  onDeveloperChange,
  onDateChange,
}: Props) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="w-48">
        <Text className="mb-1">Team</Text>
        <Select value={selectedTeam} onValueChange={onTeamChange}>
          <SelectItem value="">All teams</SelectItem>
          {teams.map((team) => (
            <SelectItem key={team} value={team}>
              {team}
            </SelectItem>
          ))}
        </Select>
      </div>

      <div className="w-48">
        <Text className="mb-1">Developer (timeline)</Text>
        <Select value={selectedDeveloper} onValueChange={onDeveloperChange}>
          {developers.map((dev) => (
            <SelectItem key={dev} value={dev}>
              {dev}
            </SelectItem>
          ))}
        </Select>
      </div>

      <div className="w-48">
        <Text className="mb-1">Timeline date</Text>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => onDateChange(e.target.value)}
          className="w-full rounded-tremor-default border border-tremor-border bg-tremor-background px-3 py-2 text-tremor-default text-tremor-content-emphasis shadow-tremor-input outline-none focus:border-tremor-brand-subtle"
        />
      </div>
    </div>
  );
}
