export type BusinessComplexity =
  | 'simple_business_page'
  | 'medium_business_page'
  | 'complex_business_page'
  | 'very_complex_business_page';

export type FixtureStatus = 'planned' | 'implemented' | 'tested' | 'deferred';

export interface BasicFixtureMeta {
  fixture_id: string;
  title: string;
  platform: 'pc' | 'mobile';
  business_complexity: BusinessComplexity;
  page_type: string;
  route: string;
  phase: string;
  runtime_behaviors: string[];
  runtime_conditions: string[];
  current_mvp_expected_observation: string;
  future_expected_observation: string;
  status: FixtureStatus;
}

export const BASIC_FIXTURES: BasicFixtureMeta[] = [
  {
    fixture_id: 'basic-login',
    title: 'Login state surfaces',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'login',
    route: '/runtime-observation/basic/login',
    phase: '11.2.4.2',
    runtime_behaviors: ['input_to_validation_message', 'submit_to_delayed_success'],
    runtime_conditions: ['normal_network', 'frontend_validation_error'],
    current_mvp_expected_observation:
      'URL or title changes only if the fixture navigates.',
    future_expected_observation: 'form_validation_message and toast_shown.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-register',
    title: 'Register state surfaces',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'register',
    route: '/runtime-observation/basic/register',
    phase: '11.2.4.2',
    runtime_behaviors: ['input_to_validation_message', 'submit_to_delayed_success'],
    runtime_conditions: ['normal_network', 'frontend_validation_error'],
    current_mvp_expected_observation:
      'URL or title changes only if the fixture navigates.',
    future_expected_observation: 'form_validation_message and toast_shown.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-sms-login',
    title: 'SMS login state surfaces',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'sms_login',
    route: '/runtime-observation/basic/sms-login',
    phase: '11.2.4.2',
    runtime_behaviors: [
      'input_to_validation_message',
      'request_code_countdown',
      'submit_to_delayed_success',
    ],
    runtime_conditions: ['normal_network', 'frontend_validation_error'],
    current_mvp_expected_observation:
      'URL or title changes only if the fixture navigates.',
    future_expected_observation:
      'form_validation_message, element_enabled, and toast_shown.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-search',
    title: 'Simple search result refresh',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'simple_search',
    route: '/runtime-observation/basic/search',
    phase: '11.2.4.2',
    runtime_behaviors: ['click_to_loading_then_result', 'empty_result'],
    runtime_conditions: ['normal_network', 'empty_result'],
    current_mvp_expected_observation:
      'May record network_idle_observed as supporting evidence only.',
    future_expected_observation: 'loading_finished and list_changed.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-detail',
    title: 'Simple detail refresh',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'simple_detail',
    route: '/runtime-observation/basic/detail',
    phase: '11.2.4.2',
    runtime_behaviors: ['click_to_loading_then_result', 'not_found_state'],
    runtime_conditions: ['normal_network', 'missing_data'],
    current_mvp_expected_observation:
      'URL or title changes only if the fixture navigates.',
    future_expected_observation: 'text_appeared and loading_finished.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-settings',
    title: 'Simple settings toggle',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'simple_settings',
    route: '/runtime-observation/basic/settings',
    phase: '11.2.4.2',
    runtime_behaviors: ['toggle_to_enabled', 'submit_to_delayed_success'],
    runtime_conditions: ['normal_network'],
    current_mvp_expected_observation:
      'No primary signal unless URL or title changes.',
    future_expected_observation: 'element_enabled and toast_shown.',
    status: 'implemented',
  },
  {
    fixture_id: 'basic-confirm',
    title: 'Simple confirm surface',
    platform: 'pc',
    business_complexity: 'simple_business_page',
    page_type: 'simple_confirm',
    route: '/runtime-observation/basic/confirm',
    phase: '11.2.4.2',
    runtime_behaviors: ['open_confirm_surface', 'confirm_to_success'],
    runtime_conditions: ['normal_network'],
    current_mvp_expected_observation:
      'No primary signal unless URL or title changes.',
    future_expected_observation: 'modal_opened and toast_shown.',
    status: 'implemented',
  },
];

export function getFixtureMeta(id: string): BasicFixtureMeta | undefined {
  return BASIC_FIXTURES.find((f) => f.fixture_id === id);
}
