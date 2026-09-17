# Security Controls

## Purpose

This document describes the security controls implemented in the Secure CI/CD Pipeline, the risks each control addresses, where each control operates, and the limitations of each control.

The project uses multiple controls because no single security scanner can evaluate every layer of software delivery.

The control model is:

**Prevent → Detect → Evaluate → Enforce**

---

## Defense-in-Depth Approach

The pipeline evaluates several distinct security surfaces:

- Credentials and secrets
- Application source code
- Third-party dependencies
- Infrastructure as Code
- Container images
- Vulnerability policy
- Security exceptions
- Continuous Integration enforcement

A successful result from one control does not imply that the other security surfaces are secure.

For example:

**Clean source code does not guarantee secure dependencies.**

**Secure dependencies do not guarantee secure infrastructure.**

**Secure application code does not guarantee a secure container image.**

This is why the pipeline uses layered controls.

---

## GitHub Push Protection

### Control Type

Preventive

### Purpose

GitHub Push Protection helps prevent supported secrets from being pushed to the remote repository.

### Project Demonstration

During development, a real Docker Personal Access Token was accidentally included in the GitHub Actions workflow.

GitHub detected the credential and blocked the push.

The token was removed from the workflow and replaced with a reference to a GitHub repository secret.

The credential was treated as exposed and required rotation.

### Architectural Lesson

Preventing a credential from reaching the remote repository reduces exposure, but it does not mean the credential should continue to be trusted.

Once a real credential has been placed into source-controlled content, credential rotation is the safer response.

### Limitation

Push Protection is not a replacement for secrets management or repository scanning.

It is one preventive layer.

---

## Gitleaks

### Control Type

Detective with pipeline enforcement

### Security Function

Secrets scanning

### Purpose

Gitleaks examines repository content for patterns associated with:

- API keys
- Access tokens
- Passwords
- Private credentials
- Other sensitive authentication material

### Project Demonstration

A synthetic secret was intentionally committed to the repository.

Gitleaks detected the secret and caused the Continuous Integration pipeline to fail.

The test secret was removed while the security control remained enabled.

### Architectural Lesson

The correct response to a security finding is generally to remediate the underlying problem rather than disable the control that discovered it.

### Important Consideration

Deleting a secret from the current version of a Git repository does not necessarily remove it from Git history.

A real exposed credential should be revoked or rotated.

### Limitation

Secrets scanners depend on detection patterns and cannot guarantee identification of every possible sensitive value.

---

## Bandit

### Control Type

Detective with pipeline enforcement

### Security Function

Static Application Security Testing

### Purpose

Bandit examines Python source code for potentially insecure coding patterns.

### Project Demonstration

Intentionally insecure subprocess code was introduced into `app.py`.

Bandit detected security issues related to command execution.

The insecure code was then removed and the scan returned to a successful state.

### Architectural Lesson

Static Application Security Testing evaluates code without requiring the application to be running.

It provides early feedback about potentially unsafe implementation patterns.

### Limitation

Bandit does not provide complete application security coverage.

It does not replace:

- Dependency vulnerability scanning
- Dynamic testing
- Container scanning
- Threat modeling
- Architecture review
- Manual security testing

It also primarily identifies patterns covered by its rules rather than every possible application vulnerability.

---

## pip-audit

### Control Type

Detective with pipeline enforcement

### Security Function

Software Composition Analysis

### Purpose

pip-audit evaluates Python packages against known vulnerability information.

### Project Demonstration

The project's dependency baseline was scanned rather than assumed to be secure.

A dependency vulnerability was identified during development and the dependency could then be evaluated against the available fixed version.

### Architectural Lesson

Third-party dependencies create software supply-chain risk even when internally developed application code is secure.

Software Composition Analysis therefore evaluates a different security surface from Static Application Security Testing.

### Control Relationship

**Bandit → Application source**

**pip-audit → Third-party Python packages**

### Limitation

Software Composition Analysis depends on available vulnerability intelligence.

A package that has no known vulnerability today may later become associated with a newly disclosed vulnerability.

---

## Checkov

### Control Type

Detective in the current lab configuration

### Security Function

Infrastructure as Code scanning

### Purpose

Checkov evaluates Terraform configuration for insecure cloud infrastructure patterns and configuration weaknesses.

### Project Demonstration

The project contains AWS S3 configuration that produces multiple Checkov findings, including controls related to areas such as encryption, versioning, public access protection, lifecycle configuration, and replication.

The findings were intentionally left visible while the workflow used:

`continue-on-error: true`

### Architectural Lesson

Detection and enforcement are separate architectural decisions.

A security tool can identify a problem without automatically blocking delivery.

### Current Lab Decision

**Checkov Finding → Report → Pipeline Continues**

This configuration was selected to demonstrate risk visibility without expanding the learning project into remediation of every Infrastructure as Code finding.

### Production Consideration

A production organization could establish blocking policies based on:

- Severity
- Resource type
- Data classification
- Environment
- Regulatory requirements
- Organizational security standards
- Approved exceptions

### Limitation

`continue-on-error` should not be confused with a formal risk exception.

It simply changes pipeline behavior.

A governed security exception requires explicit risk ownership, approval, scope, expiration, and remediation expectations.

---

## Docker Build

### Control Role

Security boundary rather than a scanner

### Purpose

The Docker build creates the deployable application artifact.

This is important because the artifact contains components that are not necessarily visible from application source-code analysis alone.

These can include:

- Operating-system packages
- Runtime libraries
- Base-image components
- Application dependencies

### Architectural Lesson

The build changes the object being evaluated.

Before build:

**Source-controlled inputs**

After build:

**Deployable artifact**

The resulting image therefore requires its own security analysis.

---

## Docker Scout

### Control Type

Detective with policy-based enforcement

### Security Function

Container vulnerability scanning

### Purpose

Docker Scout evaluates the built container image against vulnerability intelligence.

### Project Demonstration

Scanning identified Critical and High vulnerabilities in packages inherited through the container image.

The Python base image was updated from Python 3.10 slim to Python 3.12 slim.

The change reduced some vulnerability exposure but did not eliminate all blocking findings.

The resulting scan contained 15 Critical or High vulnerabilities across five packages.

### Architectural Lesson

Changing a base image can alter the vulnerability profile, but a newer image should not simply be assumed secure.

The artifact must still be scanned.

### Vulnerability Intelligence

Container vulnerability results can change over time even when application code does not.

New vulnerability disclosures or updated advisory information can cause a previously acceptable image to fail later.

### Limitation

A vulnerability scanner identifies known technical conditions.

It does not independently determine:

- Business impact
- Application exposure
- Risk ownership
- Risk acceptance
- Deployment authorization

Those decisions belong to the policy and governance layers.

---

## SARIF Security Results

### Control Role

Machine-readable security interface

### Purpose

Docker Scout exports relevant findings to:

`scout-results.sarif`

The structured output allows Python logic to evaluate actual scanner findings.

### Architectural Lesson

Machine-readable scanner output provides a cleaner integration boundary than parsing human-readable console messages.

The flow becomes:

**Scanner → Structured Finding → Policy Engine**

This also keeps the detection tool separate from organizational risk logic.

### Repository Treatment

The SARIF output is generated during execution and is excluded from Git source control.

---

## Security Severity Policy

### Component

`security_policy.py`

### Purpose

The policy translates vulnerability severity into a default organizational treatment.

| Severity | Decision |
|---|---|
| Critical | BLOCK |
| High | BLOCK |
| Medium | REVIEW |
| Low | ALLOW |

### Architectural Lesson

Scanner severity and organizational action are different concepts.

The scanner provides information about the vulnerability.

The organization defines what action should follow.

Keeping these responsibilities separate makes policy easier to understand and modify.

---

## Security Exception Registry

### Component

`security-exceptions.json`

### Control Type

Governance control

### Purpose

The exception registry represents formally accepted risk that cannot currently be remediated.

An exception can record:

- Vulnerability identifier
- Component
- Version
- Severity
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

### Project Demonstration

A High-severity zlib vulnerability with no available fixed version was used to demonstrate the exception process.

The vulnerability remained High severity.

The approved exception changed how the deployment gate treated that specific risk.

### Architectural Principle

**Risk acceptance does not eliminate the vulnerability.**

It changes the organization's decision about whether the identified risk may temporarily proceed.

---

## Exception Validation

### Component

`exception_check.py`

### Control Type

Preventive policy gate

### Purpose

The script evaluates actual Docker Scout findings against the security exception registry.

For an exception to be honored, it must:

- Match the vulnerability
- Have `APPROVED` status
- Be unexpired

### Project Demonstration

The complete scan contained 15 blocking findings.

One finding had a valid exception.

The other findings did not.

The overall result remained:

**BLOCK**

A controlled test containing only the excepted vulnerability resulted in:

**ALLOW**

### Architectural Lesson

An exception must be scoped to a specific risk.

One approved exception must never become a mechanism for bypassing unrelated security findings.

---

## Aggregate Security Gate

### Control Type

Preventive

### Purpose

The aggregate gate determines whether any unresolved blocking finding remains after policy and exception evaluation.

### Decision Logic

**No unresolved blocking findings → ALLOW**

**One or more unresolved blocking findings → BLOCK**

### Project Demonstration

The gate initially exposed an implementation issue where the console displayed an overall BLOCK decision but the process still returned exit code 0.

The exit logic was corrected to use the aggregate decision.

The resulting behavior became:

**BLOCK → Exit Code 1**

**ALLOW → Exit Code 0**

### Architectural Lesson

The final enforcement signal must represent the complete security state rather than the last individual record processed.

---

## GitHub Actions Enforcement

### Control Type

Centralized preventive control

### Purpose

GitHub Actions converts the security gate's process exit code into pipeline behavior.

### Enforcement

**Exit Code 0 → Job may continue**

**Exit Code 1 → Job fails**

### Architectural Lesson

Security policy becomes enforceable only when it is connected to a technical decision point.

The complete chain is:

**Finding → Policy → Exception → Aggregate Decision → Exit Code → CI Enforcement**

---

## Machine Identity Controls

### Purpose

The GitHub Actions runner requires authentication to services used during pipeline execution.

The runner cannot rely on a developer's local Docker login because the runner is an independent ephemeral environment.

Docker authentication is therefore provided through GitHub repository secrets.

### Architectural Lesson

Pipeline automation introduces machine identities.

These identities should be managed using principles such as:

- Least privilege
- Scoped permissions
- Secure credential storage
- Credential rotation
- Non-interactive authentication
- Auditability

Human authentication and machine authentication are separate architecture concerns.

---

## Control Classification

| Control | Function | Current Behavior |
|---|---|---|
| GitHub Push Protection | Secret prevention | Preventive |
| Gitleaks | Secrets scanning | Blocking |
| Bandit | Static Application Security Testing | Blocking |
| pip-audit | Software Composition Analysis | Blocking |
| Checkov | Infrastructure as Code scanning | Non-blocking |
| Docker Scout | Container vulnerability detection | Feeds policy gate |
| Security Policy | Severity treatment | Decision control |
| Exception Registry | Risk acceptance | Governance control |
| Exception Validation | Exception enforcement | Blocking when invalid |
| Aggregate Gate | Overall security decision | Preventive |
| GitHub Actions | CI enforcement | Preventive |

---

## Controls Not Yet Implemented

The current project intentionally does not attempt to implement every possible software-delivery security control.

Potential future controls include:

- Software Bill of Materials generation
- Artifact signing
- Artifact integrity verification
- Dynamic Application Security Testing
- Test-environment security validation
- Production deployment approvals
- Runtime application monitoring
- Container runtime protection
- Automated exception reassessment
- Central vulnerability-management integration

These represent extensions to the architecture rather than requirements for demonstrating the current control model.

---

## Security Architecture Takeaway

The most important lesson from the control architecture is that security tools do not operate in isolation.

Each control answers a different question:

**Did we expose a secret?**

**Did we write insecure code?**

**Are our dependencies vulnerable?**

**Is our infrastructure configuration secure?**

**Does the built artifact contain vulnerabilities?**

**What does organizational policy require?**

**Has a specific risk been formally accepted?**

**Should delivery be allowed to continue?**

A secure CI/CD architecture connects those answers into a governed decision process:

**Prevent → Detect → Evaluate → Decide → Enforce → Record**
