# Secure CI/CD Pipeline Architecture

## Architecture Overview

This project separates the secure software delivery process into three primary security responsibilities:

**Detection → Policy Evaluation → Enforcement**

Security scanning tools are responsible for detecting potential security issues. They do not independently represent the organization's final risk decision.

The architecture uses GitHub Actions as the centralized Continuous Integration orchestration layer. Individual security tools inspect different portions of the software delivery process, including source code, credentials, dependencies, Infrastructure as Code, and the built container image.

For container vulnerabilities, Docker Scout produces structured vulnerability findings in SARIF format. Python-based policy logic then evaluates those findings against the defined severity policy and the approved security exception registry.

The resulting aggregate decision is translated into a process exit code that GitHub Actions can enforce:

**Finding → Policy → Exception Check → Aggregate Decision → Exit Code → Pipeline Enforcement**

This separation allows scanning technology, organizational security policy, exception governance, and Continuous Integration enforcement to remain distinct architectural responsibilities.

---

## High-Level Architecture

The implemented security flow is:

**Developer**  
↓  
**Git Commit / Push**  
↓  
**GitHub Repository**  
↓  
**GitHub Actions Continuous Integration Pipeline**  
↓  
**Security Controls**
- Gitleaks — Secrets scanning
- Bandit — Static Application Security Testing
- pip-audit — Software Composition Analysis
- Checkov — Infrastructure as Code scanning

↓  
**Container Build**  
↓  
**Docker Scout — Container Vulnerability Scanning**  
↓  
**SARIF Security Findings**  
↓  
**Python Security Policy and Exception Evaluation**  
↓  
**Aggregate ALLOW / BLOCK Decision**  
↓  
**Process Exit Code**  
↓  
**GitHub Actions Enforcement**

The architecture intentionally places different controls at different stages because each control evaluates a different risk surface.

---

## Security Control Placement

### Secrets Scanning

Gitleaks operates against the source repository and attempts to identify credentials, tokens, keys, and other secrets that should not be stored in source control.

This control occurs before application deployment because exposed credentials represent a source-control and supply-chain risk independent of whether the application itself builds successfully.

The project also demonstrated GitHub Push Protection when a Docker Personal Access Token was accidentally included in a workflow change. Push Protection prevented the credential from reaching the remote repository.

This demonstrates two complementary controls:

**Preventive Control — Push Protection**

**Detective Control — Gitleaks**

A real exposed credential should still be revoked or rotated even when source-control protections prevent further distribution.

---

## Static Application Security Testing

Bandit evaluates the Python source code for insecure coding patterns.

During testing, intentionally insecure subprocess usage was introduced. Bandit identified multiple findings associated with command execution behavior.

The insecure code was then removed while the Bandit control remained in the pipeline.

This demonstrates an important architectural principle:

**Remediate the application rather than remove the security control that identified the problem.**

Static Application Security Testing operates against code before runtime. It therefore addresses a different risk surface from Dynamic Application Security Testing or container vulnerability scanning.

---

## Software Composition Analysis

pip-audit evaluates the application's Python dependencies against known vulnerability information.

This control exists because secure application code can still depend on vulnerable third-party software.

The architecture therefore treats application source and software dependencies as separate security surfaces:

**Application Code → Static Application Security Testing**

**Third-Party Dependencies → Software Composition Analysis**

A successful source-code scan does not prove that application dependencies are free of known vulnerabilities.

---

## Infrastructure as Code Security

Checkov evaluates Terraform configuration stored in the repository.

The project intentionally includes simple AWS S3 configuration that produces security findings.

For this learning implementation, Checkov is configured as a non-blocking control using `continue-on-error`.

This is an intentional architecture decision rather than an assumption that the findings are unimportant.

It demonstrates the distinction between:

**Detection — identify and report the risk**

and

**Enforcement — prevent the delivery process from continuing**

In a production environment, Infrastructure as Code enforcement thresholds would be based on organizational security standards, resource criticality, regulatory requirements, and risk tolerance.

---

## Build Boundary

The container build represents an important architectural boundary.

Before the build, the pipeline primarily evaluates source-controlled inputs:

- Application source code
- Dependencies
- Secrets
- Infrastructure configuration

After the build, a new artifact exists: the container image.

That artifact introduces additional components and risks that may not appear directly in the application repository.

For example, the container image can inherit vulnerable operating-system packages from its base image.

Therefore:

**Secure Source Code ≠ Secure Container Image**

Container scanning occurs after the image is built because the pipeline must evaluate the artifact that would actually be delivered.

---

## Container Vulnerability Scanning

Docker Scout evaluates the built container image for known vulnerabilities.

During the project, changing the Python base image changed the vulnerability results but did not eliminate all Critical and High findings.

This demonstrated that base-image selection is itself a security architecture decision.

It also demonstrated that vulnerability information changes over time. A container that previously passed a vulnerability scan may later fail when new vulnerabilities are discovered or vulnerability intelligence is updated.

Continuous scanning is therefore important even when the application source code has not changed.

---

## Structured Security Findings

Docker Scout produces its Critical and High vulnerability results in SARIF format.

SARIF provides machine-readable structured security information rather than requiring the policy logic to parse human-readable terminal output.

The architecture uses this separation:

**Docker Scout → Detect vulnerabilities**

**SARIF → Represent findings**

**Python → Evaluate organizational policy**

**GitHub Actions → Enforce the resulting decision**

This prevents the security policy from being tightly coupled to terminal formatting or manually interpreted scanner output.

---

## Security Policy

The container security policy implemented in this project is:

| Severity | Default Decision |
|---|---|
| Critical | BLOCK |
| High | BLOCK |
| Medium | REVIEW |
| Low | ALLOW |

The scanner identifies vulnerability severity.

The security policy determines what that severity means to the delivery process.

These are separate concepts.

A High vulnerability remains High even if the organization later accepts the associated risk.

---

## Security Exception Architecture

Some vulnerabilities cannot be immediately remediated.

For example, the project identified a High-severity zlib vulnerability for which Docker Scout reported no fixed version at the time of testing.

Simply disabling the security gate would allow that vulnerability to proceed, but it would also allow unrelated vulnerabilities through.

Instead, the architecture introduces a vulnerability-specific exception registry.

Each exception can contain:

- Vulnerability identifier
- Component
- Installed version
- Severity
- Source
- Reason
- Business justification
- Risk
- Compensating controls
- Owner
- Security reviewer
- Approval status
- Creation date
- Expiration date
- Remediation plan

The exception is therefore treated as a governed risk record rather than a scanner suppression.

---

## Exception Evaluation

The Python exception gate loads two sources of information:

1. Actual Docker Scout findings from `scout-results.sarif`
2. Approved exception records from `security-exceptions.json`

Each actual vulnerability finding is evaluated.

The logic determines whether the vulnerability has a matching exception.

If an exception exists, the gate verifies that:

- The exception status is `APPROVED`
- The exception has not expired

A valid exception alters the deployment treatment of that specific finding.

It does not remove the vulnerability from the scan results.

It does not change the vulnerability severity.

It does not waive unrelated vulnerabilities.

---

## Aggregate Security Decision

The security gate evaluates the entire set of applicable container findings before determining whether the pipeline can continue.

The project demonstrated the following scenario:

**15 Critical/High findings**

One finding had a valid approved exception.

The remaining findings did not.

Therefore:

**Overall Decision = BLOCK**

The presence of one valid exception cannot convert the entire container security result to ALLOW.

This aggregation behavior prevents a significant security design flaw in which the pipeline evaluates only approved exceptions rather than evaluating all actual scanner findings.

---

## Exception Success Path

A controlled test was also performed in which the SARIF input contained only the vulnerability covered by the approved, unexpired exception.

The result was:

**Finding → Default BLOCK Policy → Valid Exception → Accepted Exception → Overall ALLOW → Exit Code 0**

This demonstrated that the exception mechanism can allow a specifically accepted risk without disabling the security gate.

The full vulnerability set was then restored and correctly returned to BLOCK.

---

## Expiration as a Security Control

Exceptions are time-bound.

An exception must be both approved and unexpired.

Conceptually:

**Approved + Unexpired → Exception may be honored**

**Approved + Expired → BLOCK**

**Not Approved → BLOCK**

This prevents an exception from automatically becoming a permanent security bypass.

The remediation plan remains relevant even when temporary risk acceptance is granted.

---

## CI Enforcement

GitHub Actions ultimately enforces the decision through the process exit status returned by the Python gate.

The relationship is:

**Python returns exit code 0 → GitHub Actions continues**

**Python returns exit code 1 → GitHub Actions fails the job**

This is the technical bridge between security policy and automated enforcement.

Printing the word `BLOCK` is not sufficient by itself. The process must return a status that the Continuous Integration platform can interpret.

The project demonstrated this directly when the aggregate decision initially printed BLOCK while an incorrect exit-code implementation still returned success. The logic was corrected so the final process exit status represents the aggregate security decision rather than the state of the last individual exception record.

---

## Centralized Versus Local Controls

Security testing can occur both locally and centrally.

Local scanning can provide developers with rapid feedback before code is committed.

However, local controls depend on the developer actually executing them.

The centralized GitHub Actions pipeline provides a consistent enforcement point after code reaches the shared repository.

The architectural model is therefore:

**Local Controls → Fast Developer Feedback**

**Centralized CI Controls → Consistent Organizational Enforcement**

Local controls complement centralized enforcement rather than replace it.

---

## Machine Identity and Authentication

GitHub Actions runners are ephemeral execution environments.

A developer's local Docker authentication is not automatically available to the runner.

The pipeline therefore requires its own non-interactive authentication mechanism.

Docker credentials are stored as GitHub repository secrets and injected into the workflow when required.

This demonstrates a broader cloud security architecture principle:

**Human identity and machine identity require separate authentication designs.**

Production environments should apply least privilege, credential rotation, controlled secret storage, and limited scope to pipeline machine identities.

---

## Security Exception Governance

The project stores exception information in the repository to make the architecture understandable and testable.

This is appropriate for the learning implementation but would require stronger governance in a production environment.

A developer should not normally be able to create a vulnerability exception and independently approve that same exception.

Production approaches could include:

- Protected repository paths
- Required security reviewers
- CODEOWNERS
- Pull-request approval requirements
- Separation of duties
- External vulnerability-management systems
- Governance, Risk, and Compliance platforms
- Ticket-based risk acceptance
- Automated expiration and reassessment

The important architectural requirement is that exception authority remain separate from ordinary development authority.

---

## Failure-Safe Behavior

The architecture is designed so that unresolved blocking findings result in a failed pipeline rather than being silently ignored.

The desired behavior is:

**Unknown or unresolved blocking risk → Do not deploy automatically**

This is particularly important when processing multiple vulnerability findings.

The final decision must represent the complete evaluated security state rather than whichever record happened to be processed last.

---

## Current Architecture Result

The completed implementation demonstrated both enforcement paths.

### Normal Vulnerability Scan

**15 Critical/High findings → 1 valid exception → remaining findings unresolved → BLOCK → exit code 1**

### Controlled Exception Test

**1 blocking finding → 1 matching approved and unexpired exception → ALLOW → exit code 0**

The normal pipeline remaining red is therefore evidence of successful enforcement rather than evidence that the security pipeline is broken.

The security control is refusing to permit delivery while blocking findings remain unresolved.

---

## Production Architecture Extensions

A production implementation could extend this architecture with:

- Software Bill of Materials generation
- Artifact signing
- Artifact integrity verification
- Trusted artifact repositories
- Dynamic Application Security Testing
- Test-environment deployment gates
- Production approval workflows
- Branch protection
- Required security checks
- Separation of duties
- Centralized security telemetry
- Vulnerability remediation tracking
- Automated exception expiration
- Risk-system integration
- Runtime security monitoring
- Supply-chain security controls
- Policy-as-code governance

These controls would extend the architecture without changing its fundamental decision model.

---

## Architectural Principle

The central architectural lesson from this project is that secure CI/CD is not simply a collection of scanning tools.

A security architecture must connect technical findings to organizational decisions and then enforce those decisions consistently.

The resulting model is:

**Detect → Evaluate → Decide → Enforce → Record**

The scanner identifies the technical condition.

Security policy determines its default treatment.

Exception governance provides controlled risk acceptance where necessary.

The aggregate gate determines whether delivery can continue.

The Continuous Integration platform enforces that decision.

Together, these components turn security scanning into an enforceable software delivery control.
