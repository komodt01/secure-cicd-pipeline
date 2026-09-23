# Security Architecture Considerations

## Purpose

This document expands the Secure CI/CD Pipeline project beyond the controls directly implemented in the lab.

It distinguishes between:

1. **Controls and architecture concepts demonstrated by the project**
2. **Additional considerations that a Security Architect would evaluate when designing an enterprise production implementation**

The additional considerations are not presented as implemented features. They identify security questions, trust relationships, control requirements, and design decisions that would need to be addressed when moving from a focused proof of concept to an enterprise CI/CD architecture.

---

# Part I — Architecture Demonstrated by the Project

## Security Control Integration

The project integrates multiple security controls into a GitHub Actions CI workflow.

Implemented security activities include:

* Repository secrets scanning with Gitleaks
* Python Static Application Security Testing with Bandit
* Python dependency vulnerability scanning with pip-audit
* Terraform Infrastructure as Code scanning with Checkov
* Container vulnerability scanning with Docker Scout
* Structured vulnerability output using SARIF
* Vulnerability-specific security exception evaluation
* Exception approval-state validation
* Exception expiration validation
* Aggregate ALLOW/BLOCK security decisions
* CI enforcement using process exit status

These controls demonstrate how security analysis can become part of the software delivery process rather than remaining a separate manual activity.

## Control Enforcement Points

The project demonstrates that not every security control must have the same enforcement behavior.

Gitleaks, Bandit, and pip-audit execute as normal CI steps and can stop the job when their commands fail.

Checkov is intentionally configured with `continue-on-error: true`, making it a detective control in this lab rather than an enforced deployment gate.

Docker Scout identifies Critical and High container vulnerabilities and exports the findings for additional evaluation.

The Python exception evaluator determines whether those blocking findings have valid security exceptions and produces the aggregate container security decision.

GitHub Actions ultimately enforces that decision through the process exit status.

This demonstrates the distinction between:

**Detection → Decision → Enforcement**

## Security Decision Separation

The project separates vulnerability detection from exception evaluation.

Docker Scout identifies vulnerabilities.

`exception_check.py` determines whether each applicable vulnerability has a valid approved exception.

GitHub Actions enforces the resulting process status.

This prevents the vulnerability scanner itself from becoming the sole source of organizational risk decisions.

## Vulnerability-Specific Exceptions

Exceptions are associated with individual vulnerability identifiers.

An approved exception for one vulnerability does not authorize unrelated vulnerabilities.

The implemented decision relationship is:

**Specific Finding → Specific Exception → Aggregate Decision**

rather than:

**Any Exception → Pipeline Bypass**

## Time-Bound Risk Acceptance

The project validates both exception approval status and expiration date.

An exception that is not approved or has expired no longer satisfies the exception criteria.

This demonstrates that security exceptions should represent temporary governed risk decisions rather than permanent suppression mechanisms.

## Aggregate Security Decisions

The project evaluates all applicable Critical and High findings before determining the final container security result.

One valid exception cannot produce an ALLOW result while another blocking vulnerability remains unresolved.

The aggregate decision therefore reflects the complete set of blocking findings presented to the exception evaluator.

## Security-Sensitive Components

Several repository components have greater security significance because changing them can influence the security outcome:

* `.github/workflows/security-ci.yml`
* `exception_check.py`
* `security-exceptions.json`
* `security_policy.py`

The project documents that these components should receive stronger protection in a production implementation.

## Credential Reduction

The project originally included Docker registry authentication even though the container image was not pushed to an external registry.

That authentication step was removed.

The implemented workflow now builds and scans the image locally within the CI job without maintaining an unnecessary Docker registry credential.

This reduces unnecessary secret exposure and removes an unused external trust relationship.

## Artifact Security

The project demonstrates that source code and the resulting container image represent different security objects.

Source-focused controls evaluate application code and dependencies.

Docker Scout evaluates the built container artifact, including vulnerabilities inherited from the base image and operating-system packages.

This demonstrates why source security alone is insufficient for understanding the security state of a deployable artifact.

## Trust and Ownership

The project identifies conceptual responsibilities for:

* Application ownership
* Security risk review
* Automated exception evaluation
* CI enforcement

The Application Team owns remediation and may request an exception.

Security Architecture or an appropriate Risk Authority should authorize risk acceptance.

The CI workload evaluates findings against approved exception state.

The CI platform enforces the resulting decision.

The lab records these responsibilities but does not independently enforce enterprise separation of duties.

---

# Part II — Additional Enterprise Architecture Considerations

The following areas were not fully implemented by this project but would need to be evaluated when designing a production CI/CD security architecture.

## Administrative Separation and Separation of Duties

Application developers should not have unrestricted authority over every component that determines whether their own software passes security controls.

A production design should evaluate separate administrative authority for:

* Application source code
* CI workflow configuration
* Security policy
* Security exception approval
* Deployment authorization
* Production environment administration

Potential controls include:

* Protected branches
* Required pull-request reviews
* CODEOWNERS
* Required security reviewers
* Protected workflow files
* Centralized security pipelines
* External risk-management systems

The objective is to prevent one actor from modifying application code, weakening the security policy, approving the resulting risk, and controlling the enforcement mechanism.

## Human Identity and Workload Identity

A production CI/CD architecture should distinguish between human identities and automated workload identities.

Human identities may include:

* Developers
* Application owners
* Security reviewers
* Platform administrators
* Production approvers

Workload identities may include:

* GitHub Actions runners
* Deployment automation
* Security scanners
* Artifact publishing processes

Each identity should receive only the permissions required for its role.

CI workloads should not automatically inherit broad administrative credentials simply because they participate in the deployment process.

## CI Workload Least Privilege

The GitHub Actions workflow itself represents a privileged workload.

A production design should explicitly evaluate:

* GitHub Actions token permissions
* Repository read/write requirements
* Artifact repository permissions
* Cloud deployment permissions
* Secret access
* Environment access
* Ability to modify releases or production resources

Permissions should be explicitly scoped rather than relying on unnecessarily broad defaults.

## Privilege Boundaries

Some actions have greater security impact than ordinary source-code changes.

Examples include:

* Changing security severity thresholds
* Disabling a scanner
* Changing `continue-on-error`
* Modifying exception evaluation logic
* Approving an exception
* Extending an exception expiration date
* Modifying deployment authorization
* Changing CI credentials or workload permissions

These actions should be treated as privileged security operations and protected accordingly.

## Software Supply Chain Security

The CI pipeline depends on software and services outside the application repository.

Examples in the lab include:

* GitHub Actions
* Python packages
* Security scanning tools
* Docker base images
* Docker Scout installation sources

A production architecture should evaluate the trust placed in each external dependency.

Potential controls include:

* Pinning GitHub Actions to immutable commit SHAs
* Pinning approved tool versions
* Approved internal package repositories
* Dependency integrity verification
* Trusted container registries
* Approved hardened base images
* Software Bill of Materials generation
* Artifact signing
* Provenance verification
* Controlled software promotion

The objective is to protect the security pipeline itself from software supply-chain compromise.

## Runtime Tool Installation

The lab dynamically installs several security tools during CI execution.

This is convenient for a learning environment but creates external dependencies during every pipeline run.

A production architecture could instead evaluate:

* Pre-approved runner images
* Internally hosted tools
* Version-pinned security utilities
* Integrity-verified installation packages
* Controlled build environments

This reduces the number of external dependencies that must be trusted during execution.

## Base Image Governance

The Dockerfile uses a public Python base image.

A production organization should define how base images are:

* Selected
* Approved
* Hardened
* Scanned
* Versioned
* Patched
* Distributed
* Retired

Organizations may maintain internally approved base images rather than allowing every development team to independently select public images.

## Fail-Open vs Fail-Closed Behavior

Every security control should have a defined response when the control itself fails.

Examples include:

* Scanner unavailable
* Scanner installation failure
* SARIF output missing
* SARIF output malformed
* Exception registry malformed
* Security policy unavailable
* External vulnerability service unavailable
* CI platform error

The architecture must determine whether each failure should:

* Block delivery
* Allow delivery
* Require manual review
* Trigger an operational alert

Security-critical enforcement controls generally require explicit fail-secure behavior rather than silently allowing delivery when a decision cannot be made.

## Scanner Failure vs Security Finding

A production pipeline should distinguish between:

**The scanner successfully ran and found no blocking issue**

and:

**The scanner did not successfully complete**

These conditions are not equivalent.

A missing result should not automatically be interpreted as evidence that the artifact is secure.

## Security Control Availability

Security tooling becomes part of the delivery dependency chain.

Organizations should consider what happens when a required security service is unavailable.

Architecture decisions may include:

* Retry behavior
* Timeout thresholds
* Manual approval paths
* Emergency deployment procedures
* Documented break-glass processes
* Incident escalation

Availability requirements for security controls should therefore be considered alongside their detection capabilities.

## Bypass Protection

A production design should evaluate how an attacker or authorized insider might attempt to bypass security controls.

Potential bypass paths include:

* Removing a scanner from the workflow
* Changing a blocking step to non-blocking
* Lowering security thresholds
* Modifying exception logic
* Creating an unauthorized exception
* Extending exception expiration
* Changing workflow triggers
* Ignoring a BLOCK exit code
* Replacing scanner output
* Deploying outside the approved pipeline

The security architecture should protect both the security controls and the paths around those controls.

## Exception Governance

The lab stores exception records in the repository.

A production organization may require stronger governance through:

* External risk-management platforms
* Security approval workflows
* Ticketing-system integration
* Named risk owners
* Business approval
* Security approval
* Expiration enforcement
* Periodic exception review
* Remediation tracking
* Audit history

Exception approval should remain separate from the team requesting the exception.

## Evidence and Auditability

A production architecture should define what evidence must be retained to demonstrate that security controls executed.

Potential evidence includes:

* Scanner results
* CI execution logs
* Exception approvals
* Risk-owner decisions
* Artifact hashes
* Deployment approvals
* Build provenance
* SBOM records
* Security gate decisions
* Production release identifiers

Evidence retention requirements may depend on regulatory obligations, internal policy, investigation requirements, and application criticality.

## Security Decision Traceability

An enterprise security gate should make it possible to determine:

* What artifact was evaluated
* Which scanners evaluated it
* Which findings existed
* Which policy version was applied
* Which exceptions were used
* Who approved those exceptions
* What final decision was produced
* Which artifact was ultimately deployed

This provides traceability from security finding to production release.

## Artifact Integrity

Passing security scans is not sufficient if the artifact that was scanned is different from the artifact that is eventually deployed.

A production architecture should ensure that the approved artifact remains unchanged after security evaluation.

Potential mechanisms include:

* Artifact hashing
* Immutable artifact repositories
* Digital signatures
* Provenance records
* Controlled promotion
* Deployment by digest rather than mutable tag

The goal is to maintain:

**Build Once → Scan → Approve → Promote the Same Artifact**

## Software Bill of Materials

An SBOM was not implemented in this project.

A production architecture could generate an SBOM during the build process to provide an inventory of software components contained in the artifact.

The SBOM can support:

* Vulnerability response
* Dependency analysis
* Software supply-chain investigations
* Compliance requirements
* Impact analysis when new vulnerabilities are disclosed

## Artifact Signing and Provenance

A production implementation could add cryptographic signing and build provenance.

These controls can provide stronger assurance about:

* Who or what produced the artifact
* Which build process created it
* Whether the artifact changed after creation
* Whether the artifact came from an approved pipeline

These controls strengthen the boundary between CI build output and downstream deployment environments.

## Secrets Management

The lab intentionally removed an unnecessary Docker registry credential.

A production pipeline may still require secrets for external systems or deployment environments.

The architecture should evaluate:

* Whether long-lived secrets are necessary
* Whether workload identity can replace stored credentials
* Secret scope
* Secret rotation
* Environment-specific secret access
* Secret auditability
* Protection against secret exposure in logs

Where possible, short-lived workload credentials should be preferred over long-lived static credentials.

## Environment Separation

The current project demonstrates CI security controls but does not implement separate development, test, staging, and production deployment environments.

A production architecture should define trust boundaries between environments.

Considerations include:

* Separate cloud accounts or subscriptions
* Separate credentials
* Separate deployment roles
* Environment-specific secrets
* Production approval requirements
* Artifact promotion
* Network isolation
* Logging and monitoring boundaries

Production should not automatically inherit the same trust level as a development environment.

## Deployment Authorization

Passing automated security controls does not necessarily mean an artifact should automatically be authorized for production.

Production deployment may require additional decisions such as:

* Change approval
* Business authorization
* Security approval
* Production readiness validation
* Maintenance-window requirements
* Emergency-change procedures

The security gate should therefore be considered one input into the broader release decision.

## Network Segmentation and VLAN Considerations

Traditional VLAN or subnet segmentation is not directly implemented or required by this CI-focused lab because the project does not deploy a persistent networked application environment.

However, network boundaries may become relevant in a production CI/CD platform.

Examples include:

* Self-hosted runner network placement
* Access from CI runners to internal services
* Access to artifact repositories
* Access to production management interfaces
* Egress restrictions from build environments
* Private package repositories
* Private cloud endpoints
* Isolation of privileged deployment runners

The appropriate mechanism could include cloud network segmentation, security groups, firewall policy, private endpoints, workload isolation, or traditional VLAN controls depending on the hosting environment.

Network segmentation should therefore be driven by actual communication requirements rather than added simply because the architecture contains security tooling.

## Runner Isolation

CI runners execute code originating from application repositories and should therefore be treated as potentially exposed execution environments.

A production architecture should evaluate:

* Ephemeral runners
* Runner isolation between repositories
* Runner isolation between trust levels
* Cleanup after builds
* Network restrictions
* Secret exposure
* Privileged container access
* Host-level access
* Production connectivity

Highly privileged deployment runners should not necessarily share the same trust domain as general-purpose build runners.

## Logging and Security Monitoring

CI/CD systems themselves should be monitored as security-relevant infrastructure.

Potential monitoring includes:

* Workflow modifications
* Security-policy changes
* Exception changes
* Failed security controls
* Repeated bypass attempts
* Unusual deployment activity
* Privilege changes
* Secret-access events
* Production deployment activity

Security monitoring should include the delivery platform, not only the deployed application.

## Operational Ownership

A production implementation should define who owns each part of the security architecture.

Potential ownership domains include:

* Application teams
* Platform engineering
* DevSecOps
* Security engineering
* Security architecture
* Vulnerability management
* Risk management
* Cloud platform teams
* Production operations

Ownership should include responsibility for remediation, policy maintenance, exception review, tooling availability, incident response, and control effectiveness.

## Control Lifecycle

Security controls require ongoing governance after implementation.

A production organization should periodically evaluate:

* Whether the control is still required
* Whether the control remains effective
* Whether thresholds remain appropriate
* Whether exceptions have accumulated
* Whether tools remain supported
* Whether new threats require additional controls
* Whether control failures are being investigated
* Whether developers are bypassing the intended process

Security architecture therefore includes the lifecycle of the control, not only its initial deployment.

---

# Part III — Architecture Review Questions

When evolving this project toward an enterprise design, the following questions should be answered.

### Identity

Who is the human or workload identity performing each action?

What credentials does that identity receive?

Can short-lived workload identity replace stored secrets?

### Privilege

Who can modify security policy?

Who can modify CI workflows?

Who can approve exceptions?

Who can authorize production deployment?

### Trust

Where does responsibility move from one system or team to another?

Which external systems must the pipeline trust?

What happens if one of those systems is compromised?

### Enforcement

Which controls merely detect?

Which controls block?

Which controls require human review?

Where is the final security decision enforced?

### Failure

What happens when a scanner fails?

What happens when required evidence is missing?

Does the system fail open or fail closed?

Is there a documented break-glass process?

### Supply Chain

Where do build tools, Actions, packages, and base images originate?

How are they approved?

How is their integrity verified?

### Artifacts

Is the artifact that was scanned the same artifact that is deployed?

Can an artifact be modified after security approval?

How is provenance established?

### Exceptions

Who requests risk acceptance?

Who approves it?

How long does the approval remain valid?

Who verifies remediation?

### Environment Separation

What separates development, test, staging, and production?

Are identities, credentials, networks, and deployment roles separated?

### Network

Does the CI workload require network access to sensitive systems?

Should runners have unrestricted outbound internet access?

Are privileged deployment paths isolated from general build workloads?

### Evidence

What proves that the security controls executed?

How long is that evidence retained?

Can an auditor or incident responder reconstruct the decision later?

### Operations

Who owns each control?

Who responds when it fails?

Who determines whether the control remains effective?

---

# Architecture Perspective

The implemented project demonstrates how security controls can be incorporated into a CI pipeline and how container vulnerability findings can be converted into governed security decisions.

An enterprise implementation would extend that foundation by addressing identity, privilege, administrative separation, supply-chain trust, artifact integrity, evidence, environment isolation, operational ownership, and secure failure behavior.

The architectural objective is not simply to add more security tools.

It is to establish a delivery system in which:

**The artifact is known, the identities are known, the controls are known, the policy is explicit, exceptions are governed, the decision is traceable, and the enforcement mechanism cannot be casually bypassed.**
