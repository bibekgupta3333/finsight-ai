# Contributing to FinSight AI

Thank you for your interest in contributing to FinSight AI! This document provides guidelines and instructions for contributing.

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
   ```bash
   git clone https://github.com/your-username/finsight-ai.git
   cd finsight-ai
   ```
3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/original-owner/finsight-ai.git
   ```
4. **Create a branch** for your changes
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💻 Development Workflow

### Setting Up Development Environment

Follow the setup instructions in [README.md](README.md#quick-start).

### Making Changes

1. **Keep changes focused** - One feature/fix per PR
2. **Follow code style** - Check `.cursorrules` and `.editorconfig`
3. **Write tests** - Add tests for new features
4. **Update documentation** - Keep docs in sync with code changes

### Code Style

#### Python (Backend)
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Format with Black
- Sort imports with isort

```bash
# Format code
black app/
isort app/

# Lint
flake8 app/
mypy app/
```

#### TypeScript (Frontend)
- Use ESLint and Prettier
- Maximum line length: 100 characters
- Use functional components and hooks

```bash
# Format code
pnpm format

# Lint
pnpm lint
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
pnpm test

# All tests
pnpm test
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(backend): add transaction categorization endpoint
fix(frontend): resolve infinite loop in useEffect
docs(deployment): update kubernetes setup guide
```

## 📝 Pull Request Process

1. **Update your branch** with the latest upstream changes
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots for UI changes
   - Ensure CI checks pass

4. **Address review feedback**
   - Make requested changes
   - Push updates to the same branch
   - Respond to comments

5. **Squash commits** if requested
   ```bash
   git rebase -i HEAD~n  # where n is number of commits
   ```

## 🐛 Reporting Bugs

When reporting bugs, include:

- **Description** - Clear description of the bug
- **Steps to Reproduce** - Detailed steps
- **Expected Behavior** - What should happen
- **Actual Behavior** - What actually happens
- **Environment** - OS, browser, versions
- **Screenshots** - If applicable
- **Logs** - Relevant error messages

Use the bug report template when creating an issue.

## 💡 Suggesting Features

When suggesting features, include:

- **Use Case** - Why is this needed?
- **Proposed Solution** - How should it work?
- **Alternatives** - Other approaches considered
- **Additional Context** - Any other relevant info

Use the feature request template when creating an issue.

## 📚 Documentation

Documentation improvements are always welcome!

- Fix typos and grammar
- Improve clarity
- Add examples
- Update outdated content
- Add missing information

Documentation files are in the `docs/` directory.

## 🧪 Testing Guidelines

### Backend Tests
- Write unit tests for new functions/classes
- Write integration tests for API endpoints
- Aim for >80% code coverage
- Use pytest fixtures for common setups

### Frontend Tests
- Test components in isolation
- Test user interactions
- Test edge cases
- Use React Testing Library

## 📦 Adding Dependencies

When adding new dependencies:

1. **Check if necessary** - Can you use existing dependencies?
2. **Evaluate package** - Is it well-maintained? Popular?
3. **Consider bundle size** - For frontend packages
4. **Document why** - Explain in PR description
5. **Update requirements** - Add to requirements.txt or package.json

## 🏷️ Issue Labels

- `bug` - Something isn't working
- `feature` - New feature request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `priority: high` - High priority
- `priority: low` - Low priority
- `in progress` - Being worked on
- `needs review` - Needs code review

## 🎯 Project Board

Check the [project board](https://github.com/your-repo/projects) for:
- Current sprint tasks
- Backlog items
- In-progress work
- Completed items

## 💬 Getting Help

- **Discord** - Join our [Discord server](https://discord.gg/finsight-ai)
- **Discussions** - Use [GitHub Discussions](https://github.com/your-repo/discussions)
- **Issues** - Create an issue for bugs or questions

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make FinSight AI better for everyone. We appreciate your time and effort!

---

Happy coding! 🚀
