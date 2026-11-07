# Judge panel

The verifier for goals a program cannot score directly: visuals, feel, style. Judges score the candidate against the **reference**, never against their own taste.

## Captures

- Pick **fixed states**: the same scenes, camera positions, inputs or moments every run, so scores compare across builds.
- For each state, capture the candidate and the matching moment in the reference material (footage, screenshots, the original running).
- A scripted replay (recorded controller inputs, a Playwright script) beats manual setup, because it reproduces each state exactly.

## Judges

- Three or more judge agents, each started with a fresh context window, so no judge inherits the builder's reasoning.
- Each judge sees reference and candidate side by side, plus a fixed **rubric**: numbered criteria, each scored 1 to 5, each score naming one concrete difference.
- A criterion's score is the median across judges. The verifier score is the mean of those medians.
- Rubric and reference captures are read-only to the builder.
- Agree the pass threshold with the user (for example, every criterion's median at 4 or above).

## Keeping it honest

- **Cap each criterion.** When one criterion absorbs many rounds without moving (one run spent around $800 matching a skybox), freeze it and move on.
- **Watch for drift.** Judges reward what is easy to see. Every so often, put the top-scoring build in front of the user next to the reference.
