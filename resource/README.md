固定 GIF 目录：

- `fixed_gif/dajiao_grow/`：打胶增长 GIF
- `fixed_gif/dajiao_shrink/`：打胶缩短 GIF
- `fixed_gif/suo_grow/`：嗦牛子增长 GIF
- `fixed_gif/suo_shrink/`：嗦牛子缩短 GIF

头像合成 GIF：

- `pk` 与 `yinpa` 使用本插件内置的双头像生成器
- 配置项里可填 `do`、`lash`，也兼容 `do_frames`、`lash_frames`
- 当前内置模板帧目录：`avatar_gif/do_frames/`、`avatar_gif/lash_frames/`

建议：

- 当前默认配置已启用媒体模式：`dajiao_media_mode` / `suo_media_mode` 默认是 `fixed_gif`，`pk_media_mode` / `yinpa_media_mode` 默认是 `avatar_gif`
- 固定 GIF 放入对应目录后即可直接生效；如果想关闭，可把对应媒体模式改为 `none`
- 头像 GIF 无需依赖其他插件
