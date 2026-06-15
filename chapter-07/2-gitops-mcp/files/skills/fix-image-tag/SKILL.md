---
name: fix-image-tag
description: |
  Diagnose an ImagePullBackOff or ErrImagePull and propose a fix by opening
  a pull request that corrects the container image tag in the Deployment
  manifest. Use this skill when the user reports that a workload is failing
  to pull its image, or when the user describes symptoms consistent with a
  bad image tag (recently changed, typo, deleted upstream tag).
when_to_use:
  - User reports ImagePullBackOff, ErrImagePull, or 'image not found'
  - User mentions a deployment is stuck or pods are not starting
  - User asks to revert an image tag to a known-working value
constraints:
  - Always propose changes via a pull request. Never apply directly.
  - Never modify resources outside the namespace the user identifies.
  - The PR title must start with '[agent]' and follow the convention
    '[agent] <verb> <resource> in <namespace>'.
  - The PR body must include a one-paragraph rationale linking the symptom
    to the root cause and citing the line that changed.
---

# Fix Image Tag

## Procedure

1. **Identify the target.** From the user's message, extract:
   - The component name (e.g. `my-first-app`)
   - The namespace (default to the component name if not specified)
   - The reported symptom (ImagePullBackOff, ErrImagePull, etc.)

2. **Read the Deployment manifest.** Call `read_file` with the path
   `<component>/k8s/deployment.yaml` from the GitOps repository. Inspect
   `spec.template.spec.containers[].image`.

3. **Decide the fix.**
   - If the image string contains an obviously invalid suffix (e.g. random
     characters, `bogus`, `nonexistent`, `does-not-exist`), revert to a
     conventional default (`:alpine` for nginx). The user's `USER.md`
     records preferred defaults.
   - If the change is recent and a previous valid tag is known, prefer the
     previous tag. State this in the PR body.
   - If you cannot identify a safe replacement, **stop and ask the user**.
     Do not guess.

4. **Open the pull request.** Call `open_pull_request` with:
   - `branch`: `agent/fix-<component>-image-tag`
   - `file_path`: `<component>/k8s/deployment.yaml`
   - `content`: the entire updated YAML (do not just send a diff)
   - `commit_message`: `Fix <component> image tag`
   - `title`: `[agent] fix <component> image tag in <namespace>`
   - `body`: a paragraph with: the symptom, the line that changed (before
     and after), and a one-line rationale.

5. **Persist what you learned.** If the fix involved reverting to a default
   the user's `USER.md` already records, no memory write is needed. If the
   user told you a new preference (e.g. "always use the slim variant"),
   call `save_to_memory` so future sessions inherit it.

## Output

Return the PR URL and number to the user, plus a one-sentence summary of
what changed and why. The user will review and merge; ArgoCD reconciles
afterward. Do not poll — your work is done when the PR is open.
