import h2o
from h2o.model import ModelBase


class H2OAutoMLBaseMixin:
    def predict(self, test_data):
        """
        Predict on a dataset.

        :param H2OFrame test_data: Data on which to make predictions.

        :returns: A new H2OFrame of predictions.

        :examples:
        >>> # Set up an H2OAutoML object
        >>> aml = H2OAutoML(max_runtime_secs=30)
        >>> # Launch an H2OAutoML run
        >>> aml.train(y=y, training_frame=train)
        >>> # Predict with top model from AutoML Leaderboard on a H2OFrame called 'test'
        >>> aml.predict(test)
        >>>
        >>> # Get AutoML object by `project_name`
        >>> get_aml = h2o.automl.get_automl(aml.project_name)
        >>> # Predict with top model from AutoML Leaderboard on a H2OFrame called 'test'
        >>> get_aml.predict(test)
        """
        return self.leader.predict(test_data)

    # ---------------------------------------------------------------------------
    # Download POJO/MOJO with AutoML
    # ---------------------------------------------------------------------------
    def download_pojo(self, path="", get_genmodel_jar=False, genmodel_name=""):
        """
        Download the POJO for the leader model in AutoML to the directory specified by path.

        If path is an empty string, then dump the output to screen.

        :param path:  An absolute path to the directory where POJO should be saved.
        :param get_genmodel_jar: if True, then also download h2o-genmodel.jar and store it in folder ``path``.
        :param genmodel_name: Custom name of genmodel jar
        :returns: name of the POJO file written.
        """
        return h2o.download_pojo(self.leader, path, get_jar=get_genmodel_jar, jar_name=genmodel_name)

    def download_mojo(self, path=".", get_genmodel_jar=False, genmodel_name=""):
        """
        Download the leader model in AutoML in MOJO format.

        :param path: the path where MOJO file should be saved.
        :param get_genmodel_jar: if True, then also download h2o-genmodel.jar and store it in folder ``path``.
        :param genmodel_name: Custom name of genmodel jar
        :returns: name of the MOJO file written.
        """
        return ModelBase.download_mojo(self.leader, path, get_genmodel_jar, genmodel_name)

    @property
    def project_name(self):
        """
        Retrieve a string indicating the project_name of the automl instance to retrieve.

        :return: a string containing the project_name
        """
        pass

    @property
    def leader(self):
        """
        Retrieve the top model from an H2OAutoML object

        :return: an H2O model

        :examples:
        >>> # Set up an H2OAutoML object
        >>> aml = H2OAutoML(max_runtime_secs=30)
        >>> # Launch an AutoML run
        >>> aml.train(y=y, training_frame=train)
        >>> # Get the best model in the AutoML Leaderboard
        >>> aml.leader
        >>>
        >>> # Get AutoML object by `project_name`
        >>> get_aml = h2o.automl.get_automl(aml.project_name)
        >>> # Get the best model in the AutoML Leaderboard
        >>> get_aml.leader
        """
        pass

    @property
    def leaderboard(self):
        """
        Retrieve the leaderboard from an H2OAutoML object

        :return: an H2OFrame with model ids in the first column and evaluation metric in the second column sorted
                 by the evaluation metric

        :examples:
        >>> # Set up an H2OAutoML object
        >>> aml = H2OAutoML(max_runtime_secs=30)
        >>> # Launch an AutoML run
        >>> aml.train(y=y, training_frame=train)
        >>> # Get the AutoML Leaderboard
        >>> aml.leaderboard
        >>>
        >>> # Get AutoML object by `project_name`
        >>> get_aml = h2o.automl.get_automl(aml.project_name)
        >>> # Get the AutoML Leaderboard
        >>> get_aml.leaderboard
        """
        pass

    @property
    def training_info(self):
        """
        Expose the name/value columns of `event_log` as a simple dictionary, for example `start_epoch`, `stop_epoch`, ...
        See :func:`event_log` to obtain a description of those key/value pairs.

        :return: a dictionary with event_log['name'] column as keys and event_log['value'] column as values.
        """
        pass

    @property
    def event_log(self):
        """
        Retrieve the backend event log from an H2OAutoML object

        :return: an H2OFrame with detailed events occurred during the AutoML training.
        """
        pass

    def get_best_model(self, algorithm, criterion=None):
        """
        Get best model of a given family/algorithm.

        :param algorithm: One of "base_model", "deep_learning", "drf", "gbm", "glm", "stacked_ensemble", "xgboost", "xrt"
        :param criterion: Criterium can be one of the metrics reported in leaderboard, if None pick the first metric
                          for each task from the following list:
                            * Regression metrics: mean_residual_deviance, rmse, mse, mae, rmsle
                            * Binomial metrics: auc, logloss, aucpr, mean_per_class_error, rmse, mse
                            * Multinomial metrics: mean_per_class_error, logloss, rmse, mse, auc, aucpr
        :return: a model or None if none of a given family is present
        :examples:
        >>> # Set up an H2OAutoML object
        >>> aml = H2OAutoML(max_runtime_secs=30)
        >>> # Launch an AutoML run
        >>> aml.train(y=y, training_frame=train)
        >>> gbm = aml.get_best_model("gbm")
        """
        def _best(leaderboard, pattern, criterion, ascending):
            # type: (h2o.H2OFrame, str, str, bool) -> h2o.model.ModelBase
            matches = leaderboard.sort(by=criterion, ascending=ascending)["model_id"].grep(pattern)
            if matches.nrow == 0:
                return None
            return h2o.get_model(self.leaderboard[int(matches[0, :]), "model_id"])

        patterns = dict(
            base_model="^(?!StackedEnsemble_)",
            deep_learning="^DeepLearning_",
            drf="^(DRF|XRT)_",
            gbm="^GBM_",
            glm="^GLM_",
            stacked_ensemble="^StackedEnsemble_",
            xgboost="^XGBoost_",
            xrt="^XRT_"
        )

        higher_is_better = ["auc", "aucpr"]

        if criterion is None:
            model_category = self.leader._model_json["output"]["model_category"]
            if "Regression" == model_category:
                criterion = "mean_residual_deviance"
            elif "Binomial" == model_category:
                criterion = "auc"
            else:
                criterion = "mean_per_class_error"

        criteria = {col.lower(): col for col in self.leaderboard.columns}

        if criterion.lower() not in criteria.keys():
            from h2o.exceptions import H2OValueError
            raise H2OValueError("Criterion \"{}\" is not present in the leaderboard!".format(criterion))

        criterion = criteria[criterion]

        if algorithm.lower() not in patterns.keys():
            from h2o.exceptions import H2OValueError
            raise H2OValueError("Incorrect model_type specified \"{}\". Has to be one of \"{}\"".format(
                algorithm,
                '", "'.join(sorted(list(patterns.keys())))
            ))

        return _best(
            leaderboard=self.leaderboard,
            pattern=patterns[algorithm.lower()],
            criterion=criterion,
            ascending=criterion.lower() not in higher_is_better
        )