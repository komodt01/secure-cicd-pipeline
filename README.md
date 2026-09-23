# Secure CI/CD Pipeline — Security Controls, Policy Gates, and Exception Management

## Project Purpose

This project demonstrates how security controls can be integrated into a CI/CD pipeline to identify and govern security risk before software reaches production.

Rather than treating security scanning as a collection of independent tools, the project focuses on the architectural decision path:

**Code Change → Security Scan → Finding → Risk Evaluation → Exception Evaluation → Deployment Gate**

GitHub Actions coordinates security controls across source code, dependencies, Infrastructure as Code, and the built container image. The container vulnerability gate demonstrates how blocking findings can be evaluated against controlled, time-bound security exceptions before the pipeline produces an overall ALLOW or BLOCK decision.

The project also demonstrates an important distinction between a vulnerability and a risk decision. Approving an exception does not remove or reduce the severity of the vulnerability. It records an explicit decision to accept that specific risk temporarily under defined conditions.

The goal is to demonstrate the security architecture behind a CI/CD pipeline: where controls operate, how findings affect delivery, where enforcement occurs, and how exceptions can be governed without creating a general security bypass.

## Security Controls Implemented

The pipeline applies security controls at different stages because each control evaluates a different type of risk.

* **Secrets Scanning — Gitleaks:** Detects credentials, tokens, and other secrets that may have been committed to source control.
* **Static Application Security Testing — Bandit:** Examines Python source code for insecure coding patterns.
* **Software Composition Analysis — pip-audit:** Evaluates Python dependencies against known vulnerability information.
* **Infrastructure as Code Scanning — Checkov:** Evaluates Terraform configuration for security and configuration risks. Checkov is intentionally configured as non-blocking in this project.
* **Container Vulnerability Scanning — Docker Scout:** Evaluates the built container image for Critical and High vulnerabilities in operating-system packages and other image components.
* **Security Exception Gate — Python:** Evaluates blocking container findings against the approved security exception registry and determines the aggregate container security decision.

## Pipeline Security Flow

The implemented pipeline follows this sequence:

1. **Code is committed and pushed to GitHub.**
2. **GitHub Actions starts the security pipeline.**
3. **Gitleaks scans the repository for exposed secrets.**
4. **Bandit performs Static Application Security Testing on the Python application.**
5. **pip-audit evaluates Python dependencies for known vulnerabilities.**
6. **Checkov evaluates the Terraform Infrastructure as Code configuration.**
7. **The application container image is built.**
8. **Docker Scout scans the image for Critical and High vulnerabilities.**
9. **Docker Scout exports the vulnerability findings as structured SARIF data.**
10. **The Python exception gate compares those findings against the security exception registry.**
11. **Matching exceptions are validated for approval status and expiration date.**
12. **The gate produces an aggregate ALLOW or BLOCK decision.**
13. **The process exit code allows GitHub Actions to enforce the decision.**

If any applicable Critical or High vulnerability does not have a valid approved exception, the gate returns **BLOCK** and exits with a non-zero status.

If every applicable vulnerability is covered by a valid approved exception, the gate returns **ALLOW** and exits successfully.

The implemented container security path is therefore:

**Detection → Exception Evaluation → Aggregate Decision → CI Enforcement**

## Security Exception Management

The project includes a structured security exception registry to demonstrate how an organization can govern a vulnerability that cannot immediately be remediated.

An exception record contains:

* Vulnerability identifier
* Affected component and installed version
* Severity
* Finding source
* Reason for the exception
* Business justification
* Residual risk
* Compensating controls
* Owner
* Security reviewer
* Approval status
* Creation and expiration dates
* Remediation plan

The existence of an exception record alone does not authorize the pipeline to continue.

The exception must:

* Match the specific vulnerability
* Have an **APPROVED** status
* Remain within its defined expiration period

An exception therefore applies only to the vulnerability identified in that record. It does not suppress or override unrelated findings.

The project demonstrates this behavior using a High-severity zlib vulnerability for which no vendor-fixed package was available at the time the exception was created.

The residual risk remains explicitly recorded:

**A High-severity vulnerability remains present in the container image until a vendor-fixed package becomes available.**

No compensating controls are claimed where none were implemented.

The exception instead documents the business justification, responsible owner, security reviewer, expiration date, and remediation plan.

The project demonstrated both outcomes:

**15 blocking findings + 1 valid exception → BLOCK**

**1 blocking finding + 1 valid exception → ALLOW**

This illustrates an important security architecture principle:

**Risk acceptance changes the deployment decision; it does not change the underlying vulnerability or its severity.**

## Container Security Gate

The implemented Docker Scout step is configured to identify:

* Critical vulnerabilities
* High vulnerabilities

These severities represent the blocking threshold used by the container security gate.

The exception evaluator then determines whether each blocking vulnerability has a matching approved and unexpired exception.

The final decision is aggregate:

**One unresolved blocking vulnerability is sufficient to keep the overall decision at BLOCK.**

Python translates that decision into a process exit code:

* **Exit code 0** — the container security gate allows the pipeline to continue.
* **Exit code 1** — the container security gate blocks the pipeline and GitHub Actions fails the job.

The implemented enforcement path is:

**Critical/High Finding → Exception Evaluation → Aggregate Decision → Exit Code → CI Enforcement**

`security_policy.py` also demonstrates the broader severity-policy model used during the project:

| Severity | Default Decision |
| -------- | ---------------- |
| Critical | BLOCK            |
| High     | BLOCK            |
| Medium   | REVIEW           |
| Low      | ALLOW            |

The current Docker Scout enforcement path is specifically scoped to Critical and High findings.

## Architecture Decisions

Several design decisions were intentionally made during this project.

**Separate detection from exception enforcement.**
Docker Scout identifies Critical and High container vulnerabilities according to the configured pipeline threshold. The Python exception gate then evaluates those blocking findings against the approved exception registry and determines whether unresolved findings require the pipeline to remain blocked.

**Use structured scanner output.**
Docker Scout findings are exported using SARIF rather than parsing human-readable terminal output. This allows the exception logic to evaluate individual vulnerability identifiers programmatically.

**Evaluate exceptions by vulnerability.**
An approved exception applies only to the vulnerability identified in the exception record. It does not bypass the container security gate for unrelated findings.

**Make exceptions time-bound.**
The gate validates approval status and expiration date. An expired exception no longer satisfies the exception criteria, causing the affected blocking vulnerability to remain unresolved.

**Aggregate risk before allowing delivery.**
The final decision considers all applicable Critical and High findings. One valid exception cannot change the overall result to ALLOW while other blocking findings remain unresolved.

**Keep Infrastructure as Code findings non-blocking for this lab.**
Checkov findings are reported without stopping the pipeline. This intentionally demonstrates the distinction between a detective control and an enforced security gate. Production enforcement thresholds would depend on organizational policy, application criticality, and risk tolerance.

**Remove unnecessary credentials.**
The container image is built and scanned locally within the CI job and is not pushed to an external registry. Docker registry authentication was therefore removed rather than maintaining an unnecessary credential and external trust relationship.

## Security Decision and Ownership Boundary

The implemented lab keeps the security policy, exception registry, and enforcement logic in the same repository so the complete security decision flow can be demonstrated end to end.

This creates an important trust boundary that would require stronger separation in a production environment.

The intended ownership model is:

* **Application Team** — owns remediation and may request a security exception.
* **Security Architecture / Risk Authority** — reviews and authorizes security exceptions according to organizational policy.
* **CI Workload** — evaluates scanner findings against approved exception state.
* **CI Platform** — enforces the resulting ALLOW or BLOCK decision.

In the current implementation, `security-exceptions.json` records the exception owner, security reviewer, approval status, expiration date, residual risk, and remediation plan.

Those fields represent the governance decision, but the repository does not independently prove or enforce who was authorized to change an exception to `APPROVED`.

Similarly, `security_policy.py`, `security-exceptions.json`, `exception_check.py`, and the GitHub Actions workflow are security-sensitive assets because modifications to them can influence the security decision or its enforcement.

A production implementation should therefore prevent an application team from independently changing application code, modifying security policy, approving its own exception, or weakening the enforcement mechanism.

Potential production controls include:

* Protected branches
* Required security reviewers
* CODEOWNERS for security-sensitive files
* Protected workflow configuration
* Separation of application and security administration
* External risk or exception-management systems
* Centralized audit logging

The architectural principle is:

**The team requesting a security exception should not be the sole authority that approves the exception or controls the mechanism that enforces it.**

A dedicated trust-boundary analysis can be added separately after the implementation review is complete.

## Current Security Result

During the completed implementation, the container scan identified **15 Critical or High vulnerabilities across 5 packages**.

The security gate evaluated the applicable vulnerabilities individually:

* One High-severity zlib vulnerability had a matching approved and unexpired exception.
* The remaining Critical and High findings did not have approved exceptions.
* The aggregate security decision was therefore **BLOCK**.
* The Python gate returned exit code **1**, causing the GitHub Actions pipeline to fail as designed.

A controlled test was also performed using only the vulnerability with the approved exception. In that scenario, the gate returned **ALLOW** with exit code **0**.

The project intentionally does not force the pipeline into a green state simply to demonstrate successful execution.

A functioning security gate should stop delivery when the defined security conditions have not been satisfied.

The remaining findings represent remediation work rather than failure of the security-control mechanism.

## Repository Structure

The repository separates the demonstration application, security logic, exception data, infrastructure configuration, and pipeline automation.

* `app.py` — Demo Python application used as the source artifact evaluated by pipeline security controls.
* `security_policy.py` — Demonstrates severity-based security policy decisions.
* `exception_check.py` — Evaluates Docker Scout findings against approved security exceptions and determines the aggregate container security decision.
* `security-exceptions.json` — Stores structured, time-bound vulnerability exception records.
* `requirements.txt` — Defines Python dependencies evaluated by pip-audit.
* `Dockerfile` — Builds the application container image.
* `infrastructure/` — Contains Terraform configuration evaluated by Checkov.
* `.github/workflows/security-ci.yml` — Defines the GitHub Actions security pipeline.
* `.gitignore` — Prevents local or generated artifacts such as scanner output from being committed.

Generated scanner output such as `scout-results.sarif` is intentionally excluded from source control. It is produced during pipeline execution and consumed by the exception gate rather than maintained as application source.

## Key Lessons Learned

This project reinforced several security architecture principles.

* **Detection and enforcement are different controls.** A scanner can identify risk without automatically determining whether delivery should continue.
* **Security thresholds should be explicit.** The implemented container gate defines Critical and High vulnerabilities as its blocking scope.
* **A finding and a risk decision are different things.** A vulnerability remains present even when the organization formally accepts the associated risk.
* **Exceptions must be governed.** Approval status, ownership, expiration, justification, residual risk, and remediation planning prevent exceptions from becoming undocumented permanent bypasses.
* **Exceptions should be narrowly scoped.** Approval of one vulnerability does not authorize unrelated findings.
* **Aggregate decisions matter.** One approved exception cannot override other unresolved blocking findings.
* **Centralized controls provide stronger enforcement.** CI provides a consistent security-control point rather than depending entirely on local developer behavior.
* **Build artifacts introduce additional risk.** Source-code scanning alone does not identify vulnerabilities inherited from container base images or operating-system packages.
* **Vulnerability information changes over time.** An artifact that passes today may be affected by vulnerabilities disclosed later.
* **Unnecessary credentials should be eliminated.** Removing unused registry authentication reduces secret exposure and eliminates an unnecessary external trust relationship.
* **Security-sensitive policy and exception mechanisms require protection.** A production architecture must protect not only application code but also the controls that determine whether that code is permitted to proceed.

## Production Considerations

This project is a learning implementation rather than a production-ready CI/CD platform.

In an enterprise implementation, security exception approval should be separated from normal application-team access. Developers should not be able to create and approve their own exceptions or independently weaken the enforcement mechanism.

Additional considerations include:

* Protected security policy and workflow files
* Required security approval for exception changes
* External exception or risk-management integration
* Artifact integrity controls
* Software Bill of Materials generation
* Artifact signing and provenance
* Deployment approvals
* Separation of duties
* Centralized audit logging
* Vulnerability remediation tracking
* Post-deployment monitoring

Production enforcement thresholds would also depend on organizational risk tolerance, application criticality, regulatory requirements, and deployment environment.

The architecture demonstrated by this project provides the foundation:

**Detect → Evaluate → Decide → Enforce → Record**
