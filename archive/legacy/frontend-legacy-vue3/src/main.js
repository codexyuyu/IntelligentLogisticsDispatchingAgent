import { createApp } from 'vue'
import {
  ElAlert, ElAside, ElButton, ElCard, ElCheckbox, ElCheckboxGroup, ElCol, ElContainer,
  ElDatePicker, ElEmpty, ElForm, ElFormItem, ElInput, ElInputNumber, ElMain, ElMenu,
  ElMenuItem, ElOption, ElProgress, ElRadioButton, ElRadioGroup, ElRow, ElSelect,
  ElStep, ElSteps, ElSubMenu, ElSwitch, ElTable, ElTableColumn, ElTag
} from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import './style.css'
const app=createApp(App)
const components=[ElAlert,ElAside,ElButton,ElCard,ElCheckbox,ElCheckboxGroup,ElCol,ElContainer,ElDatePicker,ElEmpty,ElForm,ElFormItem,ElInput,ElInputNumber,ElMain,ElMenu,ElMenuItem,ElOption,ElProgress,ElRadioButton,ElRadioGroup,ElRow,ElSelect,ElStep,ElSteps,ElSubMenu,ElSwitch,ElTable,ElTableColumn,ElTag]
components.forEach(c=>app.use(c));app.mount('#app')
