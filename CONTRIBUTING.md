# 🤝 Contributing to the Enhanced RGB Keyboard Controller

We welcome and appreciate all contributions! By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### 1. Reporting Bugs

* Search the existing issues to see if your bug has already been reported.
* If not, open a new issue with the label `bug`.
* Provide a clear, descriptive title and detailed steps to reproduce the problem.
* Include information from the **Diagnostics** tab (System Info, Hardware Status) and relevant log entries from your session.

### 2. Suggesting Enhancements

* Search the existing issues to ensure the feature hasn't been discussed.
* Open a new issue with the label `enhancement`.
* Clearly describe the proposed feature and why it would be beneficial (e.g., a new effect, better hardware detection, or improved hotkey support).

### 3. Code Contributions (Pull Requests)

1.  **Fork** the repository.
2.  Clone your fork locally: `git clone [your-fork-url]`
3.  Create a new branch for your feature or fix: `git checkout -b feature/my-new-effect` or `git checkout -b fix/issue-42`
4.  Make your changes.
5.  Ensure your code adheres to Python best practices and is tested.
    * **New Effects**: Add them as static methods to `gui/effects/library.py` and map them in `gui/effects/manager.py`.
    * **New Hardware Support**: Implement detection and control logic in `gui/hardware/controller.py`.
6.  Update documentation (e.g., `README.md`) as needed.
7.  Commit your changes with clear, descriptive messages.
8.  Push your branch and open a Pull Request (PR) against the `main` branch of the original repository.

**PR Requirements:**
* Link to the original issue being addressed (e.g., "Closes #42").
* Provide a brief summary of the changes.

## Development Environment Setup

Refer to the **Local Development** section in the `README.md` for setting up your environment. Remember to run your local application with `sudo` for full functionality testing.
