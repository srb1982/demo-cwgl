export const typeName: Record<string, string> = {
  text: '文本', number: '数字', date: '日期', datetime: '日期时间', image: '图片',
  select: '下拉选项', boolean: '开关', textarea: '多行文本',
}

export const typeColor: Record<string, string> = {
  text: 'default', number: 'purple', date: 'green', datetime: 'green', image: 'orange',
  select: 'blue', boolean: 'gold', textarea: 'default',
}

export const typeOptions = [
  { label: '文本', value: 'text', desc: '单行文本输入，适用于名称、编码等', example: '用户名、商品名称、订单编号' },
  { label: '数字', value: 'number', desc: '数字输入（含小数），适用于金额、比率等', example: '金额、评分、年龄' },
  { label: '日期', value: 'date', desc: '日期选择器，适用于出生日期、入职日期等', example: '出生日期、入职日期' },
  { label: '日期时间', value: 'datetime', desc: '日期时间选择器，适用于创建时间等', example: '创建时间、更新时间' },
  { label: '图片', value: 'image', desc: '图片/文档上传，适用于照片、证件等', example: '照片、身份证附件' },
  { label: '下拉选项', value: 'select', desc: '枚举下拉选择，需配置选项列表', example: '性别、状态、类型' },
  { label: '开关（是/否）', value: 'boolean', desc: '布尔开关，适用于是否类', example: '是否启用、是否低保' },
  { label: '多行文本', value: 'textarea', desc: '多行文本输入，适用于备注、简介等', example: '备注、描述、简介' },
]

export const formatOptions = [
  { label: '无格式限制', value: '' },
  { label: '手机号', value: 'phone' },
  { label: '身份证号', value: 'id_card' },
  { label: '邮箱', value: 'email' },
  { label: '网址', value: 'url' },
]
