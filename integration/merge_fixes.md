# Merge findings and validation limits

The original application was copied from commit `f1049b6b274be996a9e09bf11011a724905c0c76`, with all 118 original Git blob hashes checked before integration. The original GitHub repository was not edited. The combined repository also includes the research, browser-local evidence workbench, editable submission artifacts and the `/evidence/` frontend route.

## Saved-model compatibility

The [initial merge run](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39060182457) reproduced **4 failed and 21 passed** backend tests. Complaint creation failed at `LogisticRegression.predict_proba` with `AttributeError: 'LogisticRegression' object has no attribute 'multi_class'`. Its warnings reported that the bundled estimators were saved with **scikit-learn 1.9.1**, while the requirements installed **1.5.2**.

The new repository pins 1.9.1, matching the saved estimators, and adds direct deserialization checks for all five model files. The grievance-model check executes real probability inference and checks its shape, finiteness and normalization. These checks bypass the API's fallback loader so an incompatible artifact cannot be hidden by fallback behavior. Model weights and training data were not replaced. This is a runtime compatibility repair, not evidence of model accuracy or improvement.

The release and its Python requirements were checked against the [official PyPI publication](https://pypi.org/project/scikit-learn/1.9.1/). The [scikit-learn persistence guidance](https://scikit-learn.org/stable/model_persistence.html#security-maintainability-limitations) explains the version requirements. Accessed 18 October 2026.

## Interpreting CI results

The [second run](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39060796980) completed **30 backend tests** successfully and built the frontend. It still failed because a fresh runner did not recreate the ignored `.merge-work` directory after the initial merge. Both `tee` log writes and the Git-bundle export failed with `No such file or directory`; with `pipefail`, these correctly made the steps fail. The merge helper now creates its temporary directory on every run, and the bundle command also creates its parent directory independently. This fixes CI bookkeeping; it does not change application behavior.

Use the final workflow result and [ci-validation.json](ci-validation.json). A step configured with `continue-on-error` can display a successful conclusion while its actual outcome failed; the final workflow gate checks the outcomes. The initial run was correctly marked failed. The source manifest records upstream hashes separately from current file hashes and marks intentional integration changes, including the combined ignore rules and dependency correction.

The initial frontend installation reported 10 dependency advisories: 3 moderate and 7 high. Its existing lockfile is preserved. A passing build does not establish that these advisories are resolved. Dependency/security updates remain separate work before public-service deployment.

Software checks do not establish real-browser behavior, field impact, government adoption, model generalization or household eligibility. Synthetic model labels and hypothetical budgets retain their existing limitations. The current CI report records executed outcomes rather than assuming the repair passed.
