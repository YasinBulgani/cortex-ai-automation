import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import Button from '@components/common/Button';

describe('Button Component', () => {
  it('should render button with label', () => {
    render(<Button label="Click me" onPress={() => {}} />);
    const button = screen.getByText('Click me');
    expect(button).toBeDefined();
  });

  it('should call onPress when pressed', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <Button label="Click me" onPress={onPress} testID="test-button" />
    );
    const button = getByTestId('test-button');
    fireEvent.press(button);
    expect(onPress).toHaveBeenCalled();
  });

  it('should not call onPress when disabled', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <Button
        label="Click me"
        onPress={onPress}
        disabled={true}
        testID="test-button"
      />
    );
    const button = getByTestId('test-button');
    fireEvent.press(button);
    expect(onPress).not.toHaveBeenCalled();
  });

  it('should render with different variants', () => {
    const { rerender } = render(
      <Button label="Primary" onPress={() => {}} variant="primary" />
    );
    expect(screen.getByText('Primary')).toBeDefined();

    rerender(
      <Button label="Secondary" onPress={() => {}} variant="secondary" />
    );
    expect(screen.getByText('Secondary')).toBeDefined();

    rerender(<Button label="Danger" onPress={() => {}} variant="danger" />);
    expect(screen.getByText('Danger')).toBeDefined();
  });

  it('should show loading state', () => {
    const { getByTestId } = render(
      <Button label="Click me" onPress={() => {}} loading={true} testID="test-button" />
    );
    const button = getByTestId('test-button');
    expect(button).toBeDefined();
  });
});
