

-- 示例数据集
INSERT INTO `dataset` (`id`, `name`, `introduce`, `create_time`, `update_time`, `user_id`, `train_dataset`) VALUES ('1', '服装电商客服(示列数据集)', '示例数据集', '2023-08-09 18:44:23', '2023-08-09 18:44:23', '', 'template.json');
-- 插入chatglm2-6b+lora的开放参数
INSERT INTO `arithmetic_parameter` (`id`, `name`, `arithmetic`, `policy`) VALUES ('1', 'train.sh', 'chatglm2-6b', 'lora');
-- 参数
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('1', 'per_device_train_batch_size', 'str', '用于训练的批处理大小。缺省值：8', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('2', 'gradient_accumulation_steps', 'str', '梯度累加次数。缺省值：1', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('3', 'logging_steps', 'str', '日志输出间隔。缺省值：500', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('4', 'save_steps', 'str', '断点保存间隔。缺省值：500', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('5', 'learning_rate', 'str', 'AdamW 优化器的初始学习率。缺省值：5e-5', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('6', 'num_train_epochs ', 'str', '训练轮数（若非整数，则最后一轮只训练部分数据）。缺省值：3.0', '1');
INSERT INTO `maas`.`arithmetic_parameter_item` (`id`, `name`, `p_type`, `introduce`, `parameter_id`) VALUES ('7', 'lora_rank', 'str', 'LoRA 微调中的秩大小。缺省值：8', '1');

