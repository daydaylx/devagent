# DevAgent Generic Playbook

## Analysis Framework
When analyzing a codebase and change request:

1.  **Understand Context**
    - Review project structure and file relationships
    - Examine existing patterns and conventions
    - Consider the broader architectural implications
2.  **Identify Requirements**
    - Parse the goal clearly
    - Identify all affected components
    - Consider edge cases and error handling
3.  **Plan Changes**
    - Minimal scope: only change what's necessary
    - Follow existing patterns and conventions
    - Ensure backward compatibility when possible
    - Consider testing and validation needs

## Code Change Guidelines
- **Precision:** Make surgical changes, avoid unnecessary modifications
- **Consistency:** Follow existing code style and patterns
- **Safety:** Include error handling and validation
- **Testing:** Consider how changes can be verified
- **Documentation:** Update comments/docs when needed

## Diff Generation Rules
- Use proper unified diff format with complete hunks
- Include sufficient context lines (3+ before and after)
- Ensure all syntax is valid and complete
- Test that diffs apply cleanly
