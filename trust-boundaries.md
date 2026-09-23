# Trust Boundary Analysis

## Purpose

This document identifies the primary trust boundaries in the Secure CI/CD Pipeline project and explains where identity, control, data, or security decision authority changes as software moves through the delivery process.

The purpose is not to treat every component as equally trusted. Instead, the architecture identifies where one actor or system hands control to another and where security controls are required to prevent an untrusted or less-trusted actor from changing the security outcome.

The implemented lab demonstrates several of these boundaries within a single GitHub repository and GitHub Actions workflow. A production implementation would require stronger separation of duties and administrative control around security-sensitive components.

## Boundary 1 — Developer to Source Repository

**Trust transition:** Developer workstation → GitHub repository

A developer creates or modifies application code, dependencies, infrastructure configuration, and other repository content before pushing those changes to GitHub.

The repository becomes the centralized source used by the CI workflow.

Security controls operating around this boundary include:

* GitHub authentication and repository authorization
* Git history and commit records
* Gitleaks repository scanning
* GitHub Push Protection where enabled
* Branch and pull-request controls in a production implementation

The primary risk at this boundary is that insecure code, exposed credentials, vulnerable dependencies, unsafe infrastructure configuration, or modifications to security-sensitive files enter the trusted delivery process.

The lab demonstrates detection through pipeline scanning. Production environments should additionally restrict who can modify security-sensitive files and require appropriate review before those changes become authoritative.

## Boundary 2 — Repository to CI Workload

**Trust transition:** Repository content → GitHub Actions runner

A push to the `main` branch causes GitHub Actions to create a CI workload and execute the security workflow defined in `.github/workflows/security-ci.yml`.

This is an important enforcement boundary because repository content transitions from stored source into executable automation.

The CI workload performs security scanning, builds the container image, evaluates container findings, and ultimately produces the process exit status used to determine whether the job succeeds or fails.

Security-sensitive assets at this boundary include:

* `.github/workflows/security-ci.yml`
* `security_policy.py`
* `exception_check.py`
* `security-exceptions.json`

Changes to these files can influence how security findings are interpreted or enforced.

In the lab, these assets exist in the same repository as the application. A production implementation should protect them through controls such as branch protection, required reviews, CODEOWNERS, protected workflow configuration, or centrally managed security pipelines.

## Boundary 3 — Source and Configuration to Security Scanners

**Trust transition:** Repository artifacts → Security analysis tools

Different security tools inspect different portions of the delivery artifact.

The implemented controls include:

* Gitleaks for repository secret scanning
* Bandit for Python static application security testing
* pip-audit for Python dependency vulnerability analysis
* Checkov for Terraform Infrastructure as Code analysis
* Docker Scout for container vulnerability analysis

The scanners are detection mechanisms. Their purpose is to identify security-relevant conditions in the artifacts presented to them.

The existence of a scanner does not by itself establish a security boundary. The boundary becomes enforceable when scanner results affect whether delivery is allowed to continue.

This distinction is demonstrated by Checkov, which is intentionally non-blocking in this lab, compared with the container vulnerability path, where unresolved Critical or High findings can cause the CI job to fail.

## Boundary 4 — Source Code to Built Container Artifact

**Trust transition:** Application source and dependencies → Container image

The Docker build creates a new artifact with a different security profile from the source repository.

The resulting container includes not only the application but also the Python runtime, operating-system packages, dependency packages, and base-image components.

This creates an artifact boundary because controls that examine source code cannot fully determine the security state of the resulting container.

Docker Scout operates after the image is built so vulnerabilities inherited from the container base image or operating-system packages can be identified.

This demonstrates why source security and artifact security are separate concerns.

A production architecture could strengthen this boundary further through artifact signing, provenance verification, Software Bill of Materials generation, trusted registries, and controlled promotion between environments.

## Boundary 5 — Scanner Findings to Security Decision

**Trust transition:** Docker Scout findings → Exception evaluation

Docker Scout exports Critical and High container vulnerability findings as SARIF.

The structured scanner output becomes an input to `exception_check.py`.

At this boundary, detection data becomes security decision input.

The exception evaluator compares each vulnerability identifier against the records stored in `security-exceptions.json`.

A finding without a matching valid exception remains unresolved and causes the aggregate decision to become BLOCK.

A matching exception is valid only when it is explicitly marked `APPROVED` and has not passed its expiration date.

The exception therefore changes the treatment of one identified vulnerability. It does not change the vulnerability severity, remove the finding, or authorize unrelated findings.

## Boundary 6 — Application Ownership to Risk Acceptance Authority

**Trust transition:** Application Team → Security Architecture / Risk Authority

This is the most important governance boundary in the project.

The Application Team owns vulnerability remediation and may have a legitimate business reason to request temporary acceptance of a security finding.

That same team should not be the sole authority that approves the risk it is requesting permission to accept.

The intended separation is:

* **Application Team** — owns remediation and provides the business justification for an exception.
* **Security Architecture / Risk Authority** — evaluates and authorizes the risk decision.
* **CI Workload** — evaluates the technical finding against approved exception state.
* **CI Platform** — enforces the resulting decision.

The current lab records the owner, security reviewer, approval status, residual risk, expiration date, and remediation plan in `security-exceptions.json`.

However, the repository does not independently enforce who is authorized to change an exception to `APPROVED`.

This is an intentionally documented limitation of the lab rather than a production separation-of-duties control.

A production implementation should prevent the requesting team from independently creating, approving, and enforcing its own exception.

## Boundary 7 — Exception Record to Enforcement Logic

**Trust transition:** Governance decision → Automated CI decision

An approved exception must be translated into an automated decision without creating a general bypass.

`exception_check.py` performs this translation.

For each applicable container vulnerability, the evaluator determines whether a matching exception exists and whether that exception is approved and unexpired.

The final decision is aggregate.

A valid exception for one vulnerability does not change the result for another vulnerability.

This protects against a failure mode in which the existence of any approved exception could accidentally cause the entire container scan to be treated as acceptable.

The architecture therefore maintains the relationship:

**Specific Finding → Specific Exception → Aggregate Decision**

rather than:

**Any Exception → Pipeline Bypass**

## Boundary 8 — Security Decision to CI Enforcement

**Trust transition:** Python decision logic → GitHub Actions job status

The exception evaluator communicates its final decision using the process exit code.

* Exit code `0` represents ALLOW.
* Exit code `1` represents BLOCK.

GitHub Actions then enforces that result through the job status.

This boundary is important because the Python script does not independently control deployment infrastructure. It communicates a decision to the CI platform, and the CI platform determines whether execution continues.

The enforcement chain is therefore:

**Finding → Exception Evaluation → Aggregate Decision → Exit Code → CI Enforcement**

Protecting only the Python logic would not be sufficient in production if an actor could independently modify the workflow to ignore the result.

The workflow itself is therefore part of the trusted security-control path.

## Boundary 9 — Implemented Lab Controls vs Production Trust

The lab intentionally places application code, security logic, exception records, and CI workflow configuration in the same repository.

This makes the complete decision path visible and testable but creates a larger shared administrative trust domain than would normally be desirable in an enterprise implementation.

The lab demonstrates:

* Security scanning across multiple artifact types
* Critical and High container vulnerability detection
* Structured SARIF output
* Vulnerability-specific exception matching
* Approval-state validation
* Exception expiration validation
* Aggregate ALLOW/BLOCK decisions
* CI enforcement through process exit status
* Explicit ownership and risk information in exception records

The lab does not claim to implement:

* Independent security administration
* Cryptographic proof of exception approval
* External risk-management integration
* Protected security policy administration
* CODEOWNERS-based security approval
* Production artifact signing
* Artifact provenance verification
* Deployment-environment authorization
* Centralized enterprise audit logging

These represent production controls that could strengthen the identified trust boundaries without changing the architectural principles demonstrated by the project.

## Security-Sensitive Assets

The following repository components have greater security significance because changing them can alter the security outcome:

* `.github/workflows/security-ci.yml` — defines the security-control sequence and determines whether control failures stop execution.
* `exception_check.py` — evaluates container findings and produces the aggregate ALLOW or BLOCK result.
* `security-exceptions.json` — records approved vulnerability exceptions and their governance metadata.
* `security_policy.py` — demonstrates the severity-based security policy model used by the project.

These components should receive stronger change protection than ordinary application code in a production implementation.

## Primary Failure and Bypass Paths

The architecture should account for attempts to bypass the security decision rather than considering only normal execution.

Important failure or bypass paths include:

* Modifying the workflow to remove or ignore a security scan.
* Changing a blocking control to non-blocking behavior.
* Modifying exception logic so unmatched vulnerabilities are allowed.
* Creating or changing an exception without independent authorization.
* Extending an exception expiration date without review.
* Changing security policy thresholds to weaken enforcement.
* Altering the CI workflow so a BLOCK exit code no longer stops execution.
* Treating one approved exception as authorization for unrelated findings.

The current lab demonstrates the decision logic but does not independently protect all of these administrative paths.

In production, these risks would be addressed through separation of duties, protected branches, required reviews, CODEOWNERS, centralized policy management, external exception approval, audit logging, and protected CI configuration.

## Architectural Principle

The central trust-boundary principle demonstrated by this project is:

**The actor producing or owning an application should not be able to independently change the security policy, approve its own risk exception, and control the mechanism that enforces that decision.**

The security architecture therefore separates the conceptual responsibilities of:

**Build → Detect → Evaluate → Approve → Enforce → Record**

even where some of those responsibilities remain implemented within a shared repository for the purposes of this lab.
