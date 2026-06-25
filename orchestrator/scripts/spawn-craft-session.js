#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

function usage() {
  console.error(`Usage:
  spawn-craft-session.js --name "Task name" --prompt-file /path/to/prompt.md [--send] [--workspace <id>]
  spawn-craft-session.js --name "Task name" --prompt "Prompt text" [--send] [--workspace <id>]`);
}

function parseArgs(argv) {
  const args = { send: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--send") {
      args.send = true;
    } else if (arg === "--name" || arg === "--prompt-file" || arg === "--prompt" || arg === "--workspace") {
      const value = argv[i + 1];
      if (!value) throw new Error(`Missing value for ${arg}`);
      args[arg.slice(2)] = value;
      i += 1;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function readActiveWorkspaceId() {
  const configPath = path.join(os.homedir(), ".craft-agent", "config.json");
  const raw = fs.readFileSync(configPath, "utf8");
  const config = JSON.parse(raw);
  if (!config.activeWorkspaceId) {
    throw new Error(`No activeWorkspaceId in ${configPath}`);
  }
  return config.activeWorkspaceId;
}

function openUrl(url) {
  const platform = process.platform;
  const commands = platform === "darwin"
    ? [["open", [url]]]
    : platform === "win32"
      ? [["cmd", ["/c", "start", "", url]]]
      : [
          ["xdg-open", [url]],
          ["gio", ["open", url]],
        ];

  const errors = [];
  for (const [cmd, args] of commands) {
    const result = spawnSync(cmd, args, { stdio: "ignore" });
    if (result.status === 0) return;
    errors.push(`${cmd}: exit ${result.status ?? "unknown"}`);
  }
  throw new Error(`Failed to open Craft Agents deep link (${errors.join("; ")})`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    usage();
    return;
  }

  if (!args.name) throw new Error("--name is required");
  if (!args["prompt-file"] && !args.prompt) throw new Error("--prompt-file or --prompt is required");

  const prompt = args["prompt-file"]
    ? fs.readFileSync(args["prompt-file"], "utf8")
    : args.prompt;
  const workspaceId = args.workspace || readActiveWorkspaceId();

  const params = new URLSearchParams();
  params.set("name", args.name);
  params.set("input", prompt);
  if (args.send) params.set("send", "true");

  const url = `craftagents://workspace/${encodeURIComponent(workspaceId)}/action/new-chat?${params.toString()}`;
  openUrl(url);
  console.log(JSON.stringify({ ok: true, name: args.name, workspaceId, sent: args.send, url }, null, 2));
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  usage();
  process.exit(1);
}
