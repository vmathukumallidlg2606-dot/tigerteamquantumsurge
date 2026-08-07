from typing import List, Dict
from .models import ExamDomain, Topic

# Define the exact 5 domains of the CompTIA Security+ SY0-701 exam
DOMAINS: List[ExamDomain] = [
    ExamDomain(
        id="domain_1",
        name="1.0 General Security Concepts",
        description="Core concepts regarding security controls, CIA triad, AAA, Zero Trust, and cryptographic primitives.",
        topics=[
            Topic(
                id="security_controls",
                name="1.1 Compare and Contrast Security Controls",
                description="Technical, Managerial, Operational, Physical controls. Preventive, Deterrent, Detective, Corrective, Compensating, Directive types.",
                key_concepts=["Technical Controls", "Physical Controls", "Preventive", "Detective", "Corrective", "Compensating"]
            ),
            Topic(
                id="fundamental_concepts",
                name="1.2 Summarize Fundamental Security Concepts",
                description="CIA triad, non-repudiation, AAA, gap analysis, Zero Trust architecture (control vs data plane), physical security, and deception/disruption technologies.",
                key_concepts=["CIA Triad", "AAA Framework", "Zero Trust", "Control Plane", "Data Plane", "Honeypots"]
            ),
            Topic(
                id="change_management",
                name="1.3 Change Management Processes",
                description="Business processes impacting security, technical implications (downtime, rollbacks, allowlists), version control, and documentation.",
                key_concepts=["Change Advisory Board (CAB)", "Backout Plan", "Rollback", "Version Control", "Impact Analysis"]
            ),
            Topic(
                id="cryptographic_solutions",
                name="1.4 Cryptographic Solutions",
                description="PKI, symmetric vs asymmetric encryption, key exchange, hashing, salting, digital signatures, key stretching, obfuscation, and certificates.",
                key_concepts=["Symmetric vs Asymmetric", "Hashing (SHA-256)", "Salting", "PKI & CAs", "Diffie-Hellman", "Digital Signatures"]
            )
        ]
    ),
    ExamDomain(
        id="domain_2",
        name="2.0 Threats, Vulnerabilities, and Mitigations",
        description="Analyzing threat actors, attack vectors, software/hardware vulnerabilities, and mitigation configurations.",
        topics=[
            Topic(
                id="threat_actors",
                name="2.1 Compare Threat Actors & Motivations",
                description="Nation-state, unskilled attackers, hacktivists, insider threats, organized crime. Motivations: exfiltration, financial gain, political, revenge.",
                key_concepts=["Insider Threat", "Nation-State", "Hacktivist", "Apt", "Data Exfiltration"]
            ),
            Topic(
                id="threat_vectors",
                name="2.2 Common Threat Vectors & Attack Surfaces",
                description="Message-based (phishing), client vs agentless software, insecure networks (wireless, Bluetooth), supply chain vulnerabilities, and social engineering.",
                key_concepts=["Phishing", "Vishing", "Smishing", "Watering Hole", "Typosquatting", "Supply Chain Risk"]
            ),
            Topic(
                id="vulnerabilities",
                name="2.3 Explain Various Types of Vulnerabilities",
                description="Application memory injection, buffer overflows, race conditions (TOC/TOU), OS/hardware vulnerabilities, virtualization escape, and misconfigurations.",
                key_concepts=["Buffer Overflow", "SQL Injection", "XSS", "TOC/TOU", "Jailbreaking", "Zero-Day"]
            ),
            Topic(
                id="malicious_indicators",
                name="2.4 Analyze Indicators of Malicious Activity",
                description="Malware attacks (ransomware, Trojans, rootkits), network attacks (DDoS, on-path, replay), application attacks, and logging anomalies.",
                key_concepts=["Ransomware", "DDoS Reflected/Amplified", "On-Path Attack", "Credential Replay", "Logic Bomb"]
            ),
            Topic(
                id="mitigation_techniques",
                name="2.5 Enterprise Mitigation Techniques",
                description="Segmentation, access control lists (ACLs), application allow lists, patching, hardening, host-based firewalls, and least privilege enforcement.",
                key_concepts=["Segmentation", "ACL", "Patching", "Least Privilege", "Host Firewalls / HIPS"]
            )
        ]
    ),
    ExamDomain(
        id="domain_3",
        name="3.0 Security Architecture",
        description="Analysing architecture models, network configurations, data protection, and resilience designs.",
        topics=[
            Topic(
                id="architecture_models",
                name="3.1 Compare Security Architecture Models",
                description="Cloud vs on-premises responsibility matrices, serverless, microservices, containerization, SDN, air-gapped networks, and SCADA/ICS IoT devices.",
                key_concepts=["Shared Responsibility", "IaC", "Containerization", "Air-Gap", "SCADA / ICS", "High Availability"]
            ),
            Topic(
                id="secure_infrastructure",
                name="3.2 Secure Enterprise Infrastructure",
                description="Device placement, security zones, network appliances (jump servers, proxies, load balancers), port security (802.1X), WAFs, and VPN tunneling.",
                key_concepts=["DMZ / Security Zones", "Jump Server", "Proxy Server", "802.1X / EAP", "WAF", "IPSec / TLS"]
            ),
            Topic(
                id="protect_data",
                name="3.3 Strategies to Protect Data",
                description="Regulated vs trade secret data classifications, data states (at rest, in transit, in use), masking, tokenization, hashing, and encryption.",
                key_concepts=["Data at Rest/Transit/Use", "Tokenization", "Data Masking", "DLP Implementation"]
            ),
            Topic(
                id="resilience_recovery",
                name="3.4 Explain Resilience & Recovery",
                description="High availability load balancing, hot/cold/warm sites, backups (snapshots, journaling), power redundancy (generators, UPS), and tabletop exercises.",
                key_concepts=["Hot / Cold / Warm Sites", "RTO / RPO", "UPS / Generators", "Tabletop Exercise"]
            )
        ]
    ),
    ExamDomain(
        id="domain_4",
        name="4.0 Security Operations",
        description="Applying security techniques to computing resources, incident response, vulnerability management, and analysis logs.",
        topics=[
            Topic(
                id="computing_resources",
                name="4.1 Secure Computing Resources",
                description="Establishing secure baselines, hardening targets (workstations, servers, RTOS), MDM management, wireless settings (WPA3), and sandboxing.",
                key_concepts=["Secure Baselines", "MDM Deployment", "WPA3 Security", "RADIUS Authentication", "Sandboxing"]
            ),
            Topic(
                id="asset_management",
                name="4.2 Hardware, Software, & Data Management",
                description="Asset procurement, monitoring, ownership classification, and disposal/decommissioning sanitization.",
                key_concepts=["Asset Inventory", "Decommissioning Sanitization", "Data Retention Policies"]
            ),
            Topic(
                id="vulnerability_activities",
                name="4.3 Vulnerability Management Activities",
                description="Vulnerability scans, static/dynamic analysis, threat feeds, CVSS scoring, CVE classification, and validation of remediation.",
                key_concepts=["Vulnerability Scanning", "SAST / DAST", "CVSS Scoring", "CVE Details", "Remediation Verification"]
            ),
            Topic(
                id="alerting_monitoring",
                name="4.4 Security Alerting and Monitoring Concepts",
                description="Log aggregation, SIEM solutions, alert tuning, antivirus tools, NetFlow, SNMP traps, and vulnerability scanners.",
                key_concepts=["SIEM Systems", "Log Aggregation", "NetFlow Analysis", "Vulnerability Scanners"]
            ),
            Topic(
                id="enhance_security",
                name="4.5 Modify Capabilities to Enhance Security",
                description="Firewall rules, web filtering, secure protocol selection, DNS filtering, email security (SPF, DKIM, DMARC), and EDR/XDR endpoints.",
                key_concepts=["SPF / DKIM / DMARC", "EDR / XDR", "Firewall Rulesets", "Web Proxy Filtering"]
            ),
            Topic(
                id="identity_access",
                name="4.6 Implement Identity and Access Management",
                description="Single sign-on (SSO, SAML, OAuth), multifactor authentication (MFA factors), password managers, and privileged access management (PAM).",
                key_concepts=["SSO / SAML / OAuth", "MFA (Factors)", "Passwordless", "Privileged Access Management (PAM)"]
            ),
            Topic(
                id="automation_orchestration",
                name="4.7 Automation & Orchestration related to Secure Operations",
                description="API integration, scripting use cases, playbooks, benefits of automation, and technical debt considerations.",
                key_concepts=["Playbook Orchestration", "API Integration", "SOAR Systems", "Workforce Multipliers"]
            ),
            Topic(
                id="incident_response",
                name="4.8 Appropriate Incident Response Activities",
                description="Preparation, detection, containment, eradication, recovery, lessons learned. Threat hunting, digital forensics, and chain of custody.",
                key_concepts=["Incident Response Lifecycle", "Chain of Custody", "Threat Hunting", "Digital Forensics"]
            ),
            Topic(
                id="data_sources",
                name="4.9 Data Sources to Support Investigations",
                description="Firewall logs, endpoint logs, OS-specific logs, packet captures, and network metadata analysis.",
                key_concepts=["Log Analysis", "Packet Capture (PCAP)", "Firewall Log Verification"]
            )
        ]
    ),
    ExamDomain(
        id="domain_5",
        name="5.0 Security Program Management and Oversight",
        description="Understanding security governance, risk analysis, third-party assessment, compliance frameworks, and audits.",
        topics=[
            Topic(
                id="security_governance",
                name="5.1 Summarize Security Governance",
                description="Acceptable Use Policies (AUP), standards (passwords, encryption), change control, governance structures, and controller responsibilities.",
                key_concepts=["AUP", "Security Policies", "Governance Structures", "Change Control"]
            ),
            Topic(
                id="risk_management",
                name="5.2 Risk Management Elements",
                description="Risk identification, assessment, qualitative vs quantitative risk analysis (SLE, ALE, ARO), risk register, and risk strategies.",
                key_concepts=["Qualitative vs Quantitative", "SLE / ALE / ARO", "Risk Register", "Risk Mitigation / Acceptance"]
            ),
            Topic(
                id="third_party_risk",
                name="5.3 Third-Party Risk Assessment & Management",
                description="Vendor assessments, service-level agreements (SLAs), Memorandums of Understanding (MOUs), non-disclosure agreements, and vendor monitoring.",
                key_concepts=["SLA / MOU / NDA", "Vendor Assessments", "Supply Chain Risk Management"]
            ),
            Topic(
                id="security_compliance",
                name="5.4 Summarize Security Compliance Elements",
                description="Compliance reporting, privacy constraints (GDPR, data subject rights), and consequences of non-compliance.",
                key_concepts=["GDPR Compliance", "Privacy / Data Sovereignty", "Compliance Monitoring"]
            ),
            Topic(
                id="audits_assessments",
                name="5.5 Audits and Assessments",
                description="Internal vs external audits, regulatory assessments, and physical vs logical penetration testing (active/passive reconnaissance).",
                key_concepts=["Internal vs External Audits", "Penetration Testing (Active/Passive)", "Compliance Audits"]
            ),
            Topic(
                id="awareness_practices",
                name="5.6 Implement Security Awareness Practices",
                description="Phishing campaigns, anomalous behavior recognition, situational awareness training, and reporting/monitoring rules.",
                key_concepts=["Phishing Simulation", "Social Engineering Awareness", "User Training Programs"]
            )
        ]
    )
]

# Flat dictionary list lookup
TOPICS: Dict[str, Topic] = {
    topic.id: topic
    for domain in DOMAINS
    for topic in domain.topics
}
