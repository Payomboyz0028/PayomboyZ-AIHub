return {
    LuaVersion = "LuaU",
    VarNamePrefix = "",
    NameGenerator = "MangledShuffled",
    PrettyPrint = false,
    Seed = 0,
    Steps = {
        { Name = "ConstantArray", Settings = { Threshold = 1, StringsOnly = true, Shuffle = true, Rotate = true } },
        { Name = "EncryptStrings", Settings = {} },
        { Name = "AntiTamper", Settings = { UseDebug = false } },
        { Name = "Vmify", Settings = {} },
        { Name = "WrapInFunction", Settings = {} },
    }
}
