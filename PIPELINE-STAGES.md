# Secure CI/CD Pipeline Stages

## Purpose

This document explains the stages of the secure CI/CD pipeline and why each security control is positioned where it is.

The pipeline follows the software delivery lifecycle rather than treating security as a single scan:

**Code → Source Control → Security Analysis → Build → Artifact Analysis → Policy Gate → Delivery Decision**

Each stage evaluates a different security risk.

---

## Stage 1 — Developer Creates or Changes Code

The process begins with application code, dependency definitions, infrastructure configuration, and pipeline configuration.

Potential risks introduced at this stage include:

- Insecure application code
- Hard-coded credentials
- Vulnerable dependencies
- Insecure infrastructure configuration
- Unsafe pipeline configuration

Developers may run security tools locally for early feedback, but local execution is not treated as the primary organizational enforcement point.

---

## Stage 2 — Git Commit and Push

Changes are committed to Git and pushed to the shared GitHub repository.

Source control provides:

- Version history
- Change traceability
- Collaboration
- Review capability
- A trigger point for centralized security automation

The project also demonstrated GitHub Push Protection when a Docker Personal Access Token was accidentally included in a workflow change.

The push was blocked before the credential reached the remote repository.

This demonstrated a preventive source-control security control.

---

## Stage 3 — Continuous Integration Pipeline Starts

A push to the repository triggers GitHub Actions.

The GitHub Actions runner provides the centralized execution environment for the security pipeline.

This creates a consistent security checkpoint that does not depend on an individual developer remembering to run security tools locally.

The runner is ephemeral, so required tools, configuration, and authentication must be established during pipeline execution.

---

## Stage 4 — Secrets Scanning

**Tool: Gitleaks**

Gitleaks examines repository content for credentials, tokens, keys, and other potential secrets.

Secrets scanning occurs early because an exposed credential is a security problem regardless of whether the application compiles, builds, or deploys successfully.

The project tested this control by intentionally committing a synthetic secret.

Gitleaks detected the secret and caused the pipeline to fail.

The synthetic secret was then removed while the scanning control remained in place.

### Security Purpose

Prevent sensitive authentication material from becoming part of the software supply chain.

---

## Stage 5 — Static Application Security Testing

**Tool: Bandit**

Bandit analyzes Python source code for insecure coding patterns.

The project intentionally introduced insecure subprocess usage and verified that Bandit detected the behavior.

The insecure code was then remediated.

Static Application Security Testing occurs before deployment because the application does not need to be running for source-code patterns to be analyzed.

### Security Purpose

Identify security weaknesses in code written by the development team.

---

## Stage 6 — Software Composition Analysis

**Tool: pip-audit**

pip-audit evaluates packages defined in `requirements.txt` against known vulnerability information.

This stage exists because application security depends on more than internally written code.

An application can contain secure custom code while still inheriting risk from vulnerable third-party dependencies.

### Security Purpose

Identify known vulnerabilities in externally maintained software dependencies.

### Architectural Distinction

**Bandit → What security problems exist in our Python code?**

**pip-audit → What known vulnerabilities exist in software packages we depend on?**

These controls are complementary rather than interchangeable.

---

## Stage 7 — Infrastructure as Code Scanning

**Tool: Checkov**

Checkov evaluates Terraform configuration before infrastructure is provisioned.

The project contains intentionally simple AWS S3 configuration that generates security findings.

For this learning implementation, Checkov is configured with `continue-on-error`, allowing findings to remain visible without stopping the entire pipeline.

This demonstrates the difference between a detective control and a preventive gate.

### Security Purpose

Identify insecure cloud infrastructure configuration before deployment.

### Current Lab Decision

**Finding → Report**

rather than:

**Finding → Automatically Block**

A production policy could enforce specific Checkov findings or severity thresholds.

---

## Stage 8 — Container Build

**Tool: Docker**

After source-oriented security analysis, the application is packaged into a container image.

This stage creates a new artifact.

The container includes more than the application source code. It can also contain:

- Base operating-system components
- Python runtime components
- Installed application dependencies
- System libraries
- Supporting packages

The security characteristics of the final image therefore cannot be determined solely from source-code scanning.

### Architectural Boundary

Before build:

**Evaluate inputs**

After build:

**Evaluate the actual artifact**

---

## Stage 9 — Container Vulnerability Scanning

**Tool: Docker Scout**

Docker Scout evaluates the built container image for known vulnerabilities.

The project filters the security results to Critical and High findings for the blocking container gate.

The scan demonstrated vulnerabilities inherited from packages contained in the base image.

Changing the Python base image changed the vulnerability profile but did not eliminate all blocking findings.

### Security Purpose

Identify vulnerabilities in the artifact that would actually be delivered.

### Architectural Distinction

**Source scan ≠ Dependency scan ≠ Container scan**

Each evaluates a different layer of the application delivery stack.

---

## Stage 10 — Structured Security Results

Docker Scout exports the relevant vulnerability findings to:

`scout-results.sarif`

SARIF provides structured, machine-readable security information.

This file becomes the interface between vulnerability detection and organizational policy evaluation.

The architecture therefore avoids making policy decisions by attempting to interpret human-readable console output.

### Flow

**Docker Scout → SARIF → Python Policy Logic**

The generated SARIF file is a runtime artifact and is excluded from source control.

---

## Stage 11 — Security Policy Evaluation

**Component: `security_policy.py`**

The project defines the following severity policy:

| Severity | Default Decision |
|---|---|
| Critical | BLOCK |
| High | BLOCK |
| Medium | REVIEW |
| Low | ALLOW |

This stage translates technical severity into organizational treatment.

The vulnerability scanner identifies the condition.

The policy determines what the organization should do about that condition.

---

## Stage 12 — Security Exception Evaluation

**Component: `exception_check.py`**

The exception gate reads:

- Actual Docker Scout SARIF findings
- The security exception registry
- Security policy logic
- Current date information

For each applicable vulnerability, the gate determines whether a matching exception exists.

A valid exception must be:

- Specifically associated with the vulnerability
- Approved
- Unexpired

A valid exception applies only to that finding.

It does not suppress other vulnerabilities.

---

## Stage 13 — Aggregate Security Decision

The gate evaluates all applicable container findings before determining the final result.

The decision is not based on only the final finding processed.

It is not based solely on whether an approved exception exists.

The gate must determine whether any unresolved blocking vulnerability remains.

### Example

**15 blocking findings**

**1 valid exception**

**14 unresolved blocking findings**

Result:

**BLOCK**

This aggregate decision prevents one approved exception from becoming a bypass for unrelated security findings.

---

## Stage 14 — Exit Code Enforcement

The Python gate converts the aggregate decision into a process exit status.

**ALLOW → Exit Code 0**

**BLOCK → Exit Code 1**

GitHub Actions interprets the exit code.

Therefore:

**Policy Decision → Process Exit Code → Pipeline Enforcement**

This is the point where security policy becomes an automated technical control.

---

## Stage 15 — Delivery Decision

If the security gate returns a blocking exit code, the GitHub Actions job fails.

If the security requirements are satisfied, the pipeline can continue to subsequent delivery stages.

The current learning implementation focuses primarily on security analysis and gate enforcement rather than implementing a complete production deployment process.

A production pipeline could continue into:

**Artifact Repository → Test Deployment → Dynamic Application Security Testing → Approval Gate → Production Deployment → Runtime Monitoring**

---

## Current Pipeline Outcome

The project currently demonstrates a real blocking condition.

The container scan identified 15 Critical or High vulnerabilities.

One High-severity vulnerability had an approved and unexpired exception.

Other blocking vulnerabilities remained.

The result was:

**Docker Scout Findings → Exception Evaluation → BLOCK → Exit Code 1 → GitHub Actions Failure**

A controlled exception-only test produced:

**Blocking Finding → Valid Exception → ALLOW → Exit Code 0**

Both paths therefore behave according to the intended architecture.

---

## Security Control Summary

| Pipeline Stage | Control | Primary Risk |
|---|---|---|
| Source Control | GitHub Push Protection | Credential exposure |
| Repository Scan | Gitleaks | Secrets committed to source |
| Source Analysis | Bandit | Insecure Python code |
| Dependency Analysis | pip-audit | Vulnerable third-party packages |
| Infrastructure Analysis | Checkov | Insecure Terraform configuration |
| Build | Docker | Creation of deployable artifact |
| Artifact Analysis | Docker Scout | Container and operating-system vulnerabilities |
| Policy Evaluation | Python | Organizational severity treatment |
| Exception Evaluation | Python + JSON | Controlled risk acceptance |
| CI Enforcement | GitHub Actions | Prevent unauthorized delivery |

---

## Architectural Takeaway

Security controls should be positioned according to the risk they are capable of evaluating.

Scanning everything at one point in the pipeline would miss important distinctions between source code, dependencies, infrastructure definitions, credentials, and built artifacts.

The pipeline therefore uses layered security controls:

**Prevent Early → Detect Early → Analyze Before Build → Inspect the Built Artifact → Evaluate Risk → Enforce the Decision**

This layered approach creates multiple opportunities to identify security problems before software reaches a production environment.
