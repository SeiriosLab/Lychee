from ikan.ChebyKAN import ChebyKAN
from ikan.GroupKAN import GroupKANLinear, GroupKAN
model = ChebyKAN(
    layers_hidden=layers_hidden,
    degree=5,
    scale_base=1.0,
    scale_cheby=1.0,
    base_activation=torch.nn.SiLU,
    use_bias=True,
)

summary(model, input_size=(64,))
