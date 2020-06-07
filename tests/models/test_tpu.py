import os
from unittest.mock import patch

import pytest
from pytorch_lightning import Trainer
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from tests.base import EvalModelTemplate

try:
    import torch_xla
    device = torch_xla.core.xla_model.xla_device()
    device_type = torch_xla.core.xla_model.xla_device_hw(device)
    TPU_AVAILABLE = device_type == 'TPU'
except ImportError:
    TPU_AVAILABLE = False


@pytest.mark.skipif(not TPU_AVAILABLE, reason="test requires TPU machine")
@pytest.mark.parametrize(['tpu_cores', 'expected_device'], [
    pytest.param([1], 'xla:1'),
    pytest.param([8], 'xla:8'),
])
def test_single_tpu_core_model(tmpdir, tpu_cores, expected_device):
    """Test if single TPU core training works"""
    trainer_options = dict(
        default_root_dir=tmpdir,
        progress_bar_refresh_rate=0,
        max_epochs=1,
        train_percent_check=0.1,
        val_percent_check=0.1,
        tpu_cores=tpu_cores
    )

    model = EvalModelTemplate()
    trainer = Trainer(**trainer_options)
    trainer.fit(model)
    assert torch_xla._XLAC._xla_get_default_device() == expected_device


@pytest.mark.spawn
@pytest.mark.parametrize("tpu_cores", [1, 8])
@pytest.mark.skipif(not TPU_AVAILABLE, reason="test requires TPU machine")
def test_multi_core_tpu_model(tmpdir, tpu_cores):
    """Test if distributed TPU core training works"""
    trainer_options = dict(
        default_root_dir=tmpdir,
        max_epochs=1,
        train_percent_check=0.4,
        val_percent_check=0.2,
        tpu_cores=tpu_cores,
    )

    model = EvalModelTemplate()
    trainer = Trainer(**trainer_options)
    trainer.fit(model)
    assert trainer.tpu_id is None


@pytest.mark.spawn
@pytest.mark.skipif(not TPU_AVAILABLE, reason="test requires TPU machine")
def test_dataloaders_passed_to_fit(tmpdir):
    """Test if dataloaders passed to trainer works on TPU"""
    trainer_options = dict(default_root_dir=tmpdir,
                           max_epochs=1,
                           tpu_cores=8,
                           )

    model = EvalModelTemplate()
    fit_options = dict(train_dataloader=model.train_dataloader(),
                       val_dataloaders=model.val_dataloader())

    trainer = Trainer(**trainer_options)
    result = trainer.fit(model, **fit_options)
    assert result, "TPU doesn't work with dataloaders passed to fit()."


@pytest.mark.spawn
@pytest.mark.parametrize("tpu_cores", [1, 8, [1]])
@pytest.mark.skipif(not TPU_AVAILABLE, reason="test requires TPU machine")
def test_mixed_precision_with_tpu(tmpdir, tpu_cores):
    """Test if FP16 TPU core training works"""
    trainer_options = dict(
        default_root_dir=tmpdir,
        max_epochs=1,
        train_percent_check=0.4,
        val_percent_check=0.2,
        tpu_cores=tpu_cores,
        precision=16
    )

    model = EvalModelTemplate()
    trainer = Trainer(**trainer_options)
    trainer.fit(model)
    assert os.environ.get('XLA_USE_BF16') == str(1), "XLA_USE_BF16 was not set in environment variables"


@pytest.mark.parametrize(['tpu_cores', 'expected_tpu_id'], [
    pytest.param(1, None),
    pytest.param(8, None),
    pytest.param([1], 1),
    pytest.param([8], 8),
])
def test_tpu_id_to_be_as_expected(tpu_cores, expected_tpu_id):
    """Test if trainer.tpu_id is set as expected"""
    assert Trainer(tpu_cores=tpu_cores).tpu_id == expected_tpu_id


@patch('pytorch_lightning.trainer.trainer.XLA_AVAILABLE', False)
def test_exception_when_no_tpu_found(tmpdir):
    """Test if exception is thrown when xla devices are not available"""
    trainer_options = dict(
        default_root_dir=tmpdir,
        max_epochs=1,
        train_percent_check=0.4,
        val_percent_check=0.2,
        tpu_cores=8,
    )

    model = EvalModelTemplate()
    trainer = Trainer(**trainer_options)

    with pytest.raises(MisconfigurationException, match='No TPU devices found.'):
        trainer.fit(model)
