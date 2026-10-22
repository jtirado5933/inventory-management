// PostToolUse hook for the Skill tool: after test/start/backend-api-test finish,
// remind Claude to hand any errors or failures to the debugger subagent.
const WATCHED_SKILLS = new Set(['test', 'start', 'backend-api-test']);

let input = '';
process.stdin.on('data', (chunk) => (input += chunk));
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(input);
  } catch {
    return;
  }

  const skill = String(payload?.tool_input?.skill ?? '').replace(/^\//, '');
  if (!WATCHED_SKILLS.has(skill)) return;

  const context =
    `The "${skill}" skill has finished. If it reported any runtime errors, stack traces, ` +
    'failing tests, or failed server startup, invoke the "debugger" subagent via the Agent tool ' +
    '(subagent_type: "debugger") with the exact error output and the command that produced it, ' +
    'then relay its root cause and suggested fix to the user. ' +
    'If everything succeeded, do nothing extra.';

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: { hookEventName: 'PostToolUse', additionalContext: context },
    })
  );
});
