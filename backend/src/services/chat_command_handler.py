"""Chat command handler for prompt execution via /slug syntax."""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import re

from ..models import PromptTemplate
from ..schemas.prompt import PromptCommandInfo


class ChatCommandHandler:
    """Handle chat commands for prompt execution."""

    def __init__(self, db: Session):
        self.db = db

    async def parse_command(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse chat message for prompt command.

        Supported formats:
        - /slug
        - /slug var1=value1 var2=value2
        - /slug "var1=value with spaces" var2=value2

        Args:
            message: Chat message to parse

        Returns:
            Dict with 'slug' and 'variables' if command found, None otherwise
        """
        if not message.startswith('/'):
            return None

        # Remove leading slash and whitespace
        message = message[1:].strip()

        # Extract slug (first word)
        parts = message.split(None, 1)
        if not parts:
            return None

        slug = parts[0]

        # Extract variables if present
        variables = {}
        if len(parts) > 1:
            # Pattern to match: var=value, var="value with spaces", var='value with spaces'
            pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))'
            matches = re.finditer(pattern, parts[1])

            for match in matches:
                var_name = match.group(1)
                # Get value from one of the capture groups (quoted or unquoted)
                var_value = match.group(2) or match.group(3) or match.group(4)
                variables[var_name] = var_value

        return {"slug": slug, "variables": variables}

    async def get_prompt_by_slug(
        self, slug: str, tenant_id: int
    ) -> Optional[PromptTemplate]:
        """Get an active, command-enabled prompt by slug."""
        return (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.slug == slug,
                PromptTemplate.is_active == True,
                PromptTemplate.is_command_enabled == True,
            )
            .first()
        )

    async def list_available_commands(
        self, tenant_id: int
    ) -> List[PromptCommandInfo]:
        """List all available commands for a tenant."""
        prompts = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
                PromptTemplate.is_command_enabled == True,
            )
            .order_by(PromptTemplate.slug)
            .all()
        )

        commands = []
        for prompt in prompts:
            # Extract required vs optional variables
            variables = prompt.variables or {}
            required_vars = [
                var for var, meta in variables.items() if meta.get("required", True)
            ]
            optional_vars = [
                var for var, meta in variables.items() if not meta.get("required", True)
            ]

            # Generate example command
            example_parts = [f"/{prompt.slug}"]
            for var in required_vars[:2]:  # Show first 2 required vars in example
                example_parts.append(f"{var}=value")
            example = " ".join(example_parts)

            commands.append(
                PromptCommandInfo(
                    slug=prompt.slug,
                    name=prompt.name,
                    description=prompt.description,
                    required_variables=required_vars,
                    optional_variables=optional_vars,
                    example=example,
                )
            )

        return commands

    async def validate_variables(
        self, prompt: PromptTemplate, provided_variables: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that all required variables are provided.

        Args:
            prompt: The prompt template
            provided_variables: Variables provided in the command

        Returns:
            Tuple of (is_valid, error_message)
        """
        variables_meta = prompt.variables or {}

        # Check for required variables
        missing_vars = []
        for var, meta in variables_meta.items():
            if meta.get("required", True) and var not in provided_variables:
                missing_vars.append(var)

        if missing_vars:
            return False, f"Missing required variables: {', '.join(missing_vars)}"

        # Check for extra variables
        extra_vars = set(provided_variables.keys()) - set(variables_meta.keys())
        if extra_vars:
            return False, f"Unknown variables: {', '.join(extra_vars)}"

        return True, None

    def format_command_help(self, prompt: PromptTemplate) -> str:
        """Format help text for a command."""
        variables_meta = prompt.variables or {}

        help_lines = [
            f"**/{prompt.slug}** - {prompt.name}",
            "",
            prompt.description or "No description available.",
            "",
            "**Usage:**",
            f"/{prompt.slug}" + (" [variables]" if variables_meta else ""),
        ]

        if variables_meta:
            help_lines.extend(["", "**Variables:**"])
            for var, meta in variables_meta.items():
                required_text = "required" if meta.get("required", True) else "optional"
                desc_text = meta.get("description", "No description")
                help_lines.append(f"  - `{var}` ({required_text}): {desc_text}")

            # Add example
            example_parts = [f"/{prompt.slug}"]
            for var in list(variables_meta.keys())[:2]:
                example_parts.append(f"{var}=value")
            help_lines.extend(["", "**Example:**", " ".join(example_parts)])

        return "\n".join(help_lines)
