# Secure CI/CD Pipeline — Security Controls, Policy Gates, and Exception Management

## Project Purpose

This project demonstrates how security controls can be integrated into a CI/CD pipeline to identify risk before software reaches production.

Rather than treating security scanning as a collection of independent tools, the project focuses on how findings move through an architectural decision process:

**Code Change → Security Scan → Finding → Policy Evaluation → Risk Decision → Deployment Gate**

The pipeline uses GitHub Actions to coordinate multiple security controls across source code, dependencies, Infrastructure as Code, and container images. Python-based policy logic is then used to demonstrate how security findings can result in an automated **ALLOW** or **BLOCK** decision.

The project also demonstrates controlled exception handling. A vulnerability does not disappear simply because an exception is approved. Instead, the vulnerability remains visible while an approved, time-bound risk exception can alter the deployment decision for that specific finding.

The goal is to demonstrate the security architecture behind a CI/CD pipeline: how controls are placed, how findings are evaluated, how enforcement occurs, and how exceptions can be governed without bypassing unrelated security findings.

## Security Controls Implemented

The pipeline applies security controls at different stages because each control evaluates a different type of risk.

* **Secrets Scanning — Gitleaks:** Detects credentials, tokens, and other secrets that may have been committed to source control.
* **Static Application Security Testing — Bandit:** Examines Python source code for insecure coding patterns before the application is built or deployed.
* **Software Composition Analysis — pip-audit:** Evaluates Python dependencies against known vulnerability information.
* **Infrastructure as Code Scanning — Checkov:** Evaluates Terraform configuration for security and configuration risks. In this project, Checkov findings are intentionally configured as non-blocking to demonstrate the difference between detection and enforcement.
* **Container Vulnerability Scanning — Docker Scout:** Scans the built container image for vulnerabilities in operating-system packages and other image components.
* **Security Policy and Exception Gate — Python:** Evaluates container vulnerability findings against security policy and approved exception records before determining whether the pipeline should continue.

## Pipeline Security Flow

The implemented pipeline follows this sequence:

1. **Code is committed and pushed to GitHub.**
2. **GitHub Actions starts the security pipeline.**
3. **Gitleaks scans the repository for exposed secrets.**
4. **Bandit performs Static Application Security Testing on the Python application.**
5. **pip-audit evaluates Python dependencies for known vulnerabilities.**
6. **Checkov evaluates the Terraform Infrastructure as Code configuration.**
7. **The application container image is built.**
8. **Docker Scout scans the built image for Critical and High vulnerabilities.**
9. **Docker Scout produces structured SARIF results containing the vulnerability findings.**
10. **The Python exception gate compares the findings against the security exception registry.**
11. **Approved exceptions are validated for status and expiration date.**
12. **The pipeline produces an overall container security decision.**

If any applicable vulnerability does not have a valid approved exception, the security gate returns **BLOCK** and exits with a non-zero status, causing the GitHub Actions job to fail.

If all applicable vulnerabilities are covered by valid exceptions, the gate returns **ALLOW** and exits successfully.

This separates three important security responsibilities:

**Detection → Policy/Exception Evaluation → Enforcement**

## Security Exception Management

The project includes a simple security exception registry to demonstrate how an organization can handle a vulnerability that cannot immediately be remediated.

An exception record includes information such as:

* Vulnerability identifier
* Affected component and installed version
* Severity
* Reason for the exception
* Business justification
* Risk
* Compensating controls
* Owner
* Security reviewer
* Approval status
* Creation and expiration dates
* Remediation plan

The pipeline does not treat the existence of an exception record as sufficient authorization to continue. The exception must have an **APPROVED** status and must not be expired.

The exception also applies only to the specific vulnerability identified in the record. It does not suppress or override unrelated findings.

This behavior was demonstrated using a High-severity zlib vulnerability for which Docker Scout reported no fixed version at the time of testing. The vulnerability remained classified as High, but an approved, time-limited exception allowed that specific finding to be treated as an accepted risk.

The project demonstrated both outcomes:

**15 blocking findings + 1 valid exception → BLOCK**

**1 blocking finding + 1 valid exception → ALLOW**

This illustrates an important security architecture principle: **risk acceptance changes the deployment decision; it does not change the underlying vulnerability or its severity.**

## Security Gate Policy

For the container vulnerability gate, the project uses the following policy:

| Severity | Default Decision |
| -------- | ---------------- |
| Critical | BLOCK            |
| High     | BLOCK            |
| Medium   | REVIEW           |
| Low      | ALLOW            |

Critical and High findings therefore prevent deployment by default.

A blocking finding may proceed only when the exception-management process identifies a matching exception that is both **approved** and **unexpired**. The exception is evaluated after the underlying policy decision rather than replacing the policy itself.

The final pipeline decision is an aggregate decision. If even one blocking vulnerability remains without a valid exception, the overall result remains **BLOCK**.

Python translates that architectural decision into a process exit code:

* **Exit code 0** — security gate allows the pipeline to continue.
* **Exit code 1** — security gate blocks the pipeline and GitHub Actions fails the job.

This creates the enforcement path:

**Security Finding → Policy Decision → Exception Evaluation → Aggregate Decision → Exit Code → CI Enforcement**

## Architecture Decisions

Several design decisions were intentionally made during this project.

**Separate detection from enforcement.**
Security scanners identify findings, but the scanner itself does not necessarily determine the organization's risk decision. Docker Scout produces the vulnerability findings, while separate Python policy logic determines whether those findings should block the pipeline.

**Use structured scanner output.**
Docker Scout findings are exported using SARIF rather than parsing human-readable terminal output. This allows the policy logic to evaluate individual vulnerability identifiers programmatically.

**Evaluate exceptions by vulnerability.**
An approved exception applies only to the vulnerability identified in the exception record. It does not bypass the container security gate for unrelated findings.

**Make exceptions time-bound.**
The gate validates both approval status and expiration date. An expired exception no longer satisfies the exception criteria and the finding returns to its default blocking behavior.

**Aggregate risk before allowing deployment.**
The final decision considers all applicable findings. One valid exception cannot change the overall result to ALLOW while other blocking findings remain unresolved.

**Keep Infrastructure as Code findings non-blocking for this lab.**
Checkov findings are currently reported without stopping the pipeline. This was an intentional learning decision to demonstrate the distinction between a detective control and an enforced security gate. In a production environment, enforcement thresholds would be defined according to organizational policy and risk tolerance.

## Security Decision and Ownership Boundary

The implemented lab keeps the security policy, exception registry, and enforcement logic in the same repository so the complete decision flow can be demonstrated end to end.

This creates an important trust boundary that would need stronger separation in a production environment.

The intended ownership model is:

* **Application Team** — remediates vulnerabilities and may request a security exception.
* **Security Architecture / Risk Authority** — reviews and authorizes security exceptions according to organizational policy.
* **CI Workload** — evaluates scanner findings against the defined policy and approved exception state.
* **CI Platform** — enforces the resulting ALLOW or BLOCK decision through the pipeline.

In the current implementation, `security-exceptions.json` records fields such as the exception owner, security reviewer, approval status, and expiration date. These fields represent the governance decision, but the repository does not independently enforce who is authorized to set an exception to `APPROVED`.

Similarly, `security_policy.py` and `exception_check.py` are security-sensitive components because changing them can change the deployment decision.

A production implementation should therefore protect the security decision path so application changes cannot independently modify security policy, approve their own exceptions, or bypass enforcement. Possible controls include protected branches, required security reviewers, CODEOWNERS for security-sensitive files, protected workflow configuration, or integration with an external risk or exception-management system.

The architectural principle is:

**The team requesting a security exception should not be the sole authority that approves the exception or controls the mechanism that enforces it.**

## Current Security Result

At the completion of this implementation, the container scan identified **15 Critical or High vulnerabilities across 5 packages**.

The security gate evaluated each vulnerability individually:

* One High-severity zlib vulnerability had a matching approved and unexpired exception.
* The remaining Critical and High findings did not have approved exceptions.
* The aggregate security decision was therefore **BLOCK**.
* The Python gate returned exit code **1**, causing the GitHub Actions pipeline to fail as designed.

A controlled test was also performed using only the vulnerability with the approved exception. In that scenario, the gate returned **ALLOW** with exit code **0**.

The project intentionally does not force the pipeline into a green state simply to demonstrate successful execution. A functioning security gate should stop delivery when the organization's defined security policy has not been satisfied.

The remaining findings represent remediation work rather than a pipeline failure.

## Repository Structure

The repository separates application logic, security policy, exception data, infrastructure configuration, and pipeline automation.

* `app.py` — Demo Python application used as the source artifact evaluated by pipeline security controls.
* `security_policy.py` — Defines severity-based security policy decisions.
* `exception_check.py` — Evaluates Docker Scout findings against approved security exceptions and determines the aggregate container security decision.
* `security-exceptions.json` — Stores structured, time-bound vulnerability exception records.
* `requirements.txt` — Defines Python dependencies evaluated by pip-audit.
* `Dockerfile` — Builds the application container image.
* `infrastructure/` — Contains Terraform configuration evaluated by Checkov.
* `.github/workflows/security-ci.yml` — Defines the centralized GitHub Actions security pipeline.
* `.gitignore` — Prevents local/generated artifacts such as scanner output from being committed.

Generated scanner output such as `scout-results.sarif` is intentionally excluded from source control. The file is produced during pipeline execution and consumed by the security gate rather than maintained as application source.

## Key Lessons Learned

This project reinforced several security architecture principles.

* **Detection and enforcement are different controls.** A scanner can identify risk without automatically preventing deployment.
* **Security policy should drive the gate.** Tool output becomes meaningful when it is evaluated against defined organizational policy.
* **A finding and a risk decision are not the same thing.** A vulnerability remains a vulnerability even when the organization formally accepts the risk.
* **Exceptions must be controlled.** Approval status, ownership, expiration, justification, and remediation planning are necessary to prevent exceptions from becoming permanent bypasses.
* **The final decision must consider all findings.** Evaluating only the exception record could accidentally allow unrelated vulnerabilities through the pipeline.
* **Centralized controls provide stronger enforcement.** Local scanning gives developers fast feedback, while the CI pipeline provides a consistent control that does not depend on an individual developer remembering to run a tool.
* **Build artifacts introduce additional risk.** Source-code scanning alone does not identify vulnerabilities inherited from the container base image or operating-system packages.
* **Vulnerability information changes over time.** An image that passes today may fail later as new vulnerabilities are identified, making continuous scanning important.
* **Unnecessary credentials should be eliminated.** The container image is built and scanned locally within the CI job and is not pushed to an external registry. Because registry authentication is not required for the implemented workflow, the Docker Hub credential and login step were removed, reducing unnecessary secret exposure and eliminating an unused external trust relationship.
* **Secret protection requires multiple layers.** Repository scanning detects exposed credentials, while GitHub Push Protection demonstrated how a preventive control can stop a credential before it reaches the remote repository.

## Production Considerations

This project is a learning implementation rather than a production-ready CI/CD platform. In an enterprise environment, additional controls would need to be considered.

Security exception approval should be separated from normal developer access. A developer should not be able to create and approve an exception simply by modifying the same repository. Production implementations could use protected files, required security reviewers, CODEOWNERS, pull-request approval rules, or integration with an external governance or risk-management system.

Additional considerations include artifact integrity, Software Bill of Materials generation, artifact signing, deployment approvals, separation of duties, centralized audit logging, exception ticket integration, vulnerability remediation tracking, and post-deployment monitoring.

The specific enforcement thresholds would also depend on organizational risk tolerance, application criticality, regulatory requirements, and the environment being deployed.

The architecture demonstrated here provides the foundation:

**Detect → Evaluate → Decide → Enforce → Record**
