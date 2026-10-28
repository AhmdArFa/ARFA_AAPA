# Skill: Trial Mode

Use when: the manager is trying the system live, with questions not collected in advance.
Do NOT collect manager questions before the trial, and do NOT build on previous questions as manager questions.
Steps: answer from registered tools if possible, otherwise abstain with available tools, and log the unanswered question locally for review after the trial.
Logging does NOT auto-add a metric, a domain, a tool, or a skill. Ahmed reviews the log, one by one, after the trial.
Forbidden: collecting manager questions before the trial, building on previous questions as manager questions, auto-adding metrics from the trial log.

Example: manager asks a new domain question during the trial -> if no tool matches, abstain with available tools, log question and missing reason, do not create a tool on the spot.
Output shape for abstention: reason, available tools, trial log entry.
Common mistake: treating a trial question as an approved metric definition.
